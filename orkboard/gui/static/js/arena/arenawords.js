// The one window's words and lists (docs/specs/49-one-window.md): pure functions over `ideas.map`, `ideas.board`, `ideas.agents`,
// `ideas.gate`, `ideas.today` and the snapshot. No signal and no template here; the parts of the window (arena.js and its
// neighbours) draw what these say. The backend writes no words: the member's state, a task's foot and a stop's text are said here.
import { leftToDo, TASK_STATE } from "../board/maplayout.js";
import { memberWords, planWords, soFarWords, todayWords } from "../board/mapstage.js";
import { holdWords, hhmm } from "../board/store.js";
import { TIER_WORDS, RACE_WORDS } from "../orkui.js";

export const SEATS = { build: 3, check: 2 };            // a party's seats beside the leader (decisions §56)
const RUN = ["running", "testing"];
const RANK = { running: 0, testing: 0, failed: 1, review: 2, ready: 3, waiting: 4, held: 5 };      // a column, from the member up (§5.4)
const LEVEL = { laborer: 1, warrior: 2, elder: 3 };      // the level's chevrons (marks/rank-1 … 3)

export const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
export const money = (n) => `$${n < 10 ? Number(n).toFixed(2) : Math.round(n)}`;
const round2 = (n) => Math.round(n * 100) / 100;
/** *$1–2*: a plan's price, from `plan_estimate`; "" with none. */
export const rangeWords = (e) => (e ? `$${round2(e.usd_low)}–${round2(e.usd_high)}` : "");

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
/** An idea at work: past its plan, not done (§4.2). */
export const atWork = (n) => n.stage === "implementation" || n.stage === "checking";
export const openTasks = (n) => (n.tasks || []).filter(leftToDo);

/** *k ideas left of n*. */
export function leftWords(g, nodes) {
  const total = g.ideas ?? nodes.length, done = g.done ?? nodes.filter((n) => n.state === "done").length;
  return `${plural(total - done, "idea", "ideas")} left of ${total}`;
}
export const costWords = (g) => [soFarWords(g.usd), todayWords(g.today)].filter(Boolean).join(" · ");

// -- the stops: what waits for the person ----------------------------------------------------------------------------------------

const STOP_KINDS = ["asks", "plan", "proposal"];                 // the stops of Planning (§4.3)
/** The goal's Planning: the ideas in stage planning that are not raw, the stops first; the raw ones apart (*New (n)*). */
export function planningOf(g, nodes, leader) {
  const lead = leader || g.leader?.name || "Taskmaster";
  const asks = (n) => n.asked?.[0]?.by?.name;
  const words = (n) => {
    if (n.needs_you === "plan") return "plan ready";
    if (n.needs_you === "asks") return `asks you · ${asks(n) || lead}`;
    if (n.needs_you === "proposal") return "proposed";
    if (n.state === "reading") return `${lead} is reading ↻`;
    if (n.state === "planning") return `${lead} is planning ↻`;
    if (n.state === "plan" && n.start_at === "night") return "starts tonight";
    if (n.state === "ready") return `ready · ${lead} plans it next`;
    return n.state;
  };
  const row = (n) => {
    const stop = STOP_KINDS.includes(n.needs_you), busy = n.state === "reading" || n.state === "planning";
    return { slug: n.slug, title: n.short || n.title, full: n.title, stop, busy, mark: stop ? "!" : busy ? "↻" : "", words: words(n),
      cost: n.needs_you === "plan" ? rangeWords(n.plan_estimate || n.estimate) : "", kind: n.needs_you === "plan" ? "plan" : "idea", node: n };
  };
  const mine = nodes.filter((n) => n.stage === "planning");
  const rows = mine.filter((n) => n.state !== "raw").map(row);
  const raw = mine.filter((n) => n.state === "raw").map((n) => ({ slug: n.slug, title: n.short || n.title, full: n.title, node: n, kind: "idea", stop: false, busy: false,
    mark: "", cost: "", words: n.queue === "hold" ? "stopped" : n.queue === "night" ? "tonight" : `new · ${lead} reads it later` }));
  return { rows: [...rows.filter((r) => r.stop), ...rows.filter((r) => !r.stop)], raw };
}

/** *Process now · 2 new ideas* / *no new idea*, the idea it reads and its tooltip (§4.4). */
export function powerOf(raw, lead) {
  const first = raw[0];
  return { slug: first?.slug || "", off: !first, words: first ? plural(raw.length, "new idea", "new ideas") : "no new idea",
    tip: first ? `${lead} reads “${first.full}” now` : "No new idea to read" };
}

// -- the party -----------------------------------------------------------------------------------------------------------------------

/** The party row (§5.1): the goal's builders, then its checkers (agents outside the party that hold a task among them), then the
 *  free seats: [{slug, name, head, band, state, why, free}]; the leader apart. */
export function partyOf(g, nodes) {
  const party = g.party || [];
  const lead = party.find((m) => m.band === "lead") || (g.leader ? { ...g.leader, band: "lead", state: "free", why: "" } : null);
  const team = party.filter((m) => m.band !== "lead").map((m) => ({ ...m, free: false }));
  const known = new Set([lead?.slug, ...team.map((m) => m.slug)]);
  for (const n of nodes.filter(atWork)) {
    for (const t of openTasks(n)) {
      if (known.has(t.by.slug)) continue;
      known.add(t.by.slug);
      const mine = nodes.filter(atWork).flatMap((x) => openTasks(x).filter((y) => y.by.slug === t.by.slug));
      const failed = mine.some((y) => y.state === "failed"), run = mine.some((y) => RUN.includes(y.state));
      team.push({ slug: t.by.slug, name: t.by.name, head: t.head, band: t.band === "check" ? "check" : "build", free: false,
        state: failed ? "needs" : run ? "work" : "next", why: failed ? "failed" : "" });
    }
  }
  const builders = team.filter((m) => m.band === "build"), checkers = team.filter((m) => m.band === "check");
  const seat = (band, i) => ({ slug: `seat-${band}-${i}`, name: "A free seat", band, free: true, state: "free", why: "" });
  const free = [...Array.from({ length: Math.max(0, SEATS.build - builders.length) }, (_, i) => seat("build", i)),
    ...Array.from({ length: Math.max(0, SEATS.check - checkers.length) }, (_, i) => seat("check", i))];
  return { lead, members: [...builders, ...checkers, ...free] };
}

export const BAND_WORDS = { lead: "Leads", build: "Builds", check: "Checks" };
export const BAND_KEYWORD = { lead: "Leads:", build: "Takes:", check: "Checks:" };

/** A member's open tasks of the ideas at work, in its column's order: the one at work nearest it, then failed, in Review, ready, waiting, held. */
export function columnOf(m, nodes) {
  const items = [];
  nodes.filter(atWork).forEach((n, i) => openTasks(n).forEach((t, j) => { if (t.by.slug === m.slug) items.push({ n, t, at: i * 1000 + j }); }));
  return items.sort((a, b) => (RANK[a.t.state] ?? 9) - (RANK[b.t.state] ?? 9) || a.t.wave - b.t.wave || a.at - b.at);
}
/** The merged tasks of a member, over all the goal's ideas (*✓ k in dev*). */
export const mergedBy = (m, nodes) => nodes.reduce((k, n) => k + (n.tasks || []).filter((t) => t.state === "merged" && t.by.slug === m.slug).length, 0);

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
  const API = "at API prices, not your bill";
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

/** What a member does now, and after (§5.2): *↻ Challenge store · 4 min*, *✗ <task>*, *next: <task>*, *n in Review*. */
export function nowOf(m, col, planning, isLead) {
  if (isLead) {
    const stops = planning.rows.filter((r) => r.stop), busy = planning.rows.find((r) => r.busy);
    const ready = [...planning.rows, ...planning.raw].find((r) => r.node.state === "ready" || r.node.state === "raw");
    const now = busy ? `↻ reading “${busy.title}”` : ready ? `next: plans “${ready.title}”` : stops.length ? `${stops[0].words}: “${stops[0].title}”` : "";
    const next = stops.length > 1 ? `${stops.length} wait for you` : stops.length === 1 && busy ? `${stops[0].words}: “${stops[0].title}”` : "";
    return { now, next };
  }
  const run = col.filter((x) => RUN.includes(x.t.state)), failed = col.find((x) => x.t.state === "failed"), held = col.find((x) => x.t.state === "held");
  const nx = col.find((x) => x.t.state === "ready" || x.t.state === "waiting"), rv = col.filter((x) => x.t.state === "review").length;
  const name = (x) => x.t.short || x.t.title, min = (x) => sinceWords(x.t.started);
  const now = run.length ? `↻ ${name(run[0])}${min(run[0]) ? ` · ${min(run[0])}` : ""}` : failed ? `✗ ${name(failed)}` : nx ? `next: ${name(nx)}` : rv ? `${rv} in Review` : "";
  const next = failed && run.length ? `✗ ${name(failed)}` : held ? `tonight: ${name(held)}` : rv && run.length ? `${rv} in Review` : nx && run.length ? `next: ${name(nx)}` : "";
  return { now, next };
}

/** A member's state in words, its colour class and what a screen reader hears. */
export function memberView(m, stats, line, race) {
  const words = memberWords(m) || "free";
  const tone = m.state === "needs" ? "is-needs" : m.state === "work" ? "" : "is-quiet";
  const label = [m.name, `${race ? `${race}, ` : ""}${stats.harness.name}, ${stats.level}`, `${words}${m.state === "work" ? ", at work" : ""}`, stats.runsTip,
    `${stats.price === "—" ? "no price yet" : `${stats.price} a run`}`, line.now].filter(Boolean).join(", ");
  return { words, tone, label: `${label}. A click shows its work.` };
}

export const raceOf = (head) => (head ? RACE_WORDS[head.race] || "" : "");

// -- the columns -------------------------------------------------------------------------------------------------------------------

/** A task's foot: its state in words (*working 4 min*, *in Review*, *after k1*, *tonight · after 01:00*, *failed*). */
export function taskFoot(t, n) {
  if (t.state === "running") return `working${sinceWords(t.started) ? ` ${sinceWords(t.started)}` : ""}`;
  if (t.state === "testing") return "testing";
  if (t.state === "review") return "in Review";
  if (t.state === "failed") return "failed";
  if (t.state === "held") {
    if (n?.waits?.kind === "night") return `tonight${n.waits.until ? ` · after ${hhmm(n.waits.until)}` : ""}`;
    return holdWords(t.note, n?.waits?.title) || "held";
  }
  if (t.state === "waiting") return t.after?.length ? `after ${t.after.join(", ")}` : "waiting";
  if (t.state === "ready") return t.note || "next";
  return TASK_STATE[t.state] || t.state;
}
export const taskMark = (t) => (RUN.includes(t.state) ? "↻" : t.state === "failed" ? "✗" : "");

/** The tasks that wait for `src` (they list it in `after`), in the same idea, not done. */
export function waitersOf(n, src) {
  return openTasks(n).filter((a) => a.id !== src.id && (a.after || []).includes(src.id));
}

/** *Only Backend's tasks* and the lists of a member shown alone: the same order as its column, across the field. */
export function rowsOf(list, per) {
  const out = [];
  for (let i = 0; i < list.length; i += per) out.push(list.slice(i, i + per));
  return out;
}

// -- the results --------------------------------------------------------------------------------------------------------------------

/** The goal's results that wait for a look, oldest first. */
export function resultsOf(nodes) {
  const all = nodes.flatMap((n) => (n.results || []).map((r) => ({ ...r, ideaTitle: n.title, ideaSlug: n.slug })));
  return all.map((r, i) => [r, i]).sort(([a, i], [b, j]) => String(a.finished || "").localeCompare(String(b.finished || "")) || i - j).map(([r]) => r);
}

// -- the ideas bar ---------------------------------------------------------------------------------------------------------------------

/** *<who> ↻ <task> (<idea>)* for every running task of the ideas at work, the leader reading, else *nothing at work right now*. */
export function nowLine(nodes, lead, readingTitle) {
  const bits = [];
  for (const n of nodes.filter(atWork)) for (const t of n.tasks.filter((x) => RUN.includes(x.state))) bits.push(`${t.by.name} ↻ ${t.short || t.title} (${n.short || n.title})`);
  if (readingTitle) bits.push(`${lead} ↻ reading “${readingTitle}”`);
  return bits.length ? bits.join(" · ") : "nothing at work right now";
}

/** An idea at work in the list: its note (§4.2). */
export function ideaNote(n, lead) {
  const tasks = n.tasks || [], failed = tasks.filter((t) => t.state === "failed"), run = tasks.filter((t) => RUN.includes(t.state)), held = tasks.filter((t) => t.state === "held");
  if (failed.length) return { text: `✗ ${failed[0].short || failed[0].title} failed`, tone: "no" };
  if (run.length) return { text: run.map((t) => `${t.by.name} ↻ ${t.short || t.title}`).join(" · "), tone: "" };
  if (held.length) return { text: `tonight: ${held[0].short || held[0].title}`, tone: "" };
  const next = tasks.find((t) => t.state === "ready" || t.state === "waiting");
  return { text: `Nothing waits for your look. Next: ${n.stage === "checking" ? "Checking" : "Implementation"}${next ? ` by ${next.by.name}` : ""}.`, tone: "" };
}

/** *in dev · waits for main* or *in main*, by what `ideas.gate` still lists. */
export function doneWords(n, gate) {
  const into = gate?.into || "dev", main = gate?.main || "main";
  const inMain = !!gate && (gate.same || !(gate.ideas || []).some((i) => i.slug === n.slug));
  return inMain ? `in ${gate.same ? into : main}` : `in ${into} · waits for ${main}`;
}

// -- the gate -------------------------------------------------------------------------------------------------------------------------

/** The gate's button, its words and whether it is off (§5.6); null with no gate to show. */
export function gateOf(gate) {
  if (!gate || gate.same) return null;
  const n = (gate.ideas || []).length, waits = gate.commits > 0;
  return { off: !waits, label: `Merge ${gate.into} into ${gate.main}`,
    words: !waits ? `${gate.main} is up to date` : n ? `${n === 1 ? "1 idea" : `${n} ideas`} in ${gate.into} ${n === 1 ? "waits" : "wait"} for ${gate.main}` : `${plural(gate.commits, "commit", "commits")} in ${gate.into} ${gate.commits === 1 ? "waits" : "wait"} for ${gate.main}` };
}

// -- today ---------------------------------------------------------------------------------------------------------------------------------

/** Today's rows of the goal shown, and the gate's (it has no goal): newest first. */
export const todayOf = (today, goal) => (today?.events || []).filter((e) => !e.goal || e.goal === goal);
export const TODAY_TONE = { ok: "is-ok", danger: "is-no", muted: "is-muted", ink: "" };
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

export const KIND_WORD = { plan: "Plan ready", asks: "Asks you", goal: "Asks you", proposal: "Proposed", party: "Proposed", todo: "A to-do", failed: "Failed",
  op: "At your check", op_failed: "Failed", op_rules: "Rules to take" };
export const isOp = (n) => n.kind === "op" || n.kind === "op_failed" || n.kind === "op_rules";
const GEM = { plan: "", asks: "?", goal: "?", proposal: "—", party: "—", todo: "·", failed: "✗", op: "·", op_failed: "✗", op_rules: "—" };

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
  const taskItem = (n, t) => ({ key: `failed/${n.slug}/${t.id}`, kind: "failed", row: null, node: n, task: t, label: KIND_WORD.failed, gem: "✗", tone: "danger",
    gemTip: "It failed", head: t.head || null, small: true, whoTip: `${t.by.name}’s task`, title: t.short || t.title, full: t.title, text: t.error || "It failed" });
  for (const row of needs.filter((x) => !isOp(x) && x.goal === g?.slug)) {
    const n = byIdea[row.idea] || null;
    if (row.kind === "failed" && n && failedTasks(n).length) {
      for (const t of failedTasks(n)) if (!done.has(`${n.slug}/${t.id}`)) { done.add(`${n.slug}/${t.id}`); out.push(taskItem(n, t)); }
      continue;
    }
    const base = { key: `${row.kind}/${row.idea || row.goal}/${row.todo?.id || ""}`, kind: row.kind, row, node: n, task: null, label: KIND_WORD[row.kind] || row.kind,
      gem: GEM[row.kind] ?? "·", tone: row.kind === "failed" ? "danger" : "alert", gemTip: "", title: row.title, full: row.title, text: row.text, head: lead, small: false, whoTip: "" };
    if (row.kind === "plan") {
      const tasks = n?.tasks || [], checks = tasks.filter((t) => t.band === "check").length, builds = tasks.length - checks;
      base.gem = rangeWords(n?.plan_estimate || n?.estimate) || "—";
      base.gemTip = "What the plan should cost, at API prices";
      if (tasks.length) base.text = `${plural(builds, "task", "tasks")}${checks ? `, ${plural(checks, "check", "checks")}` : ""}`;
    } else if (row.kind === "asks" || row.kind === "goal") {
      const q = firstAsk(row, n);
      base.text = `“${q.ask}”`; base.gemTip = "A question costs nothing";
      if (row.kind === "asks") { base.head = q.by?.head || n?.asked?.[0]?.by?.head || lead; base.small = true; base.whoTip = q.by?.name ? `asked by ${q.by.name}` : ""; }
      else base.small = false;
    } else if (row.kind === "failed") { base.small = true; base.head = lead; base.gemTip = "It failed"; }
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

/** A fan's turn, rise and order for item `i` of `n` (the middle ones higher): the values of `--rot`, `--dy` and `--z`. */
export function fanOf(i, n, fanned = true) {
  const off = i - (n - 1) / 2;
  return { rot: fanned ? Math.round(off * 5 * 10) / 10 : 0, dy: fanned ? Math.round(off * off * 4) : 0, z: 10 + i };
}

/** A result among the stops, below 1 024 px (§3): *To look at*, with a result's own answers. */
export function resultStop(r, nodes) {
  const node = nodes.find((n) => n.slug === r.idea) || null, task = node?.tasks.find((t) => t.id === r.task) || null;
  const t = r.tests && !r.check ? r.tests : null;
  return { key: `result/${r.idea}/${r.task}`, kind: "result", row: null, node, task, result: r, label: "To look at", gem: r.check ? "✓" : t && (t.failed > 0 || t.green === false) ? "✗" : "✓",
    tone: "", gemTip: "A result waits for your look", head: task?.head || null, small: true, whoTip: task ? `${task.by.name}’s task` : "", title: r.title, full: r.title,
    text: [r.diff ? `${plural(r.diff.files, "file", "files")}` : "", r.cost != null ? money(r.cost) : ""].filter(Boolean).join(" · ") };
}
