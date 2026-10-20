// The Map on the phone (docs/specs/39-map.md §5, decisions §53): the desktop's trail, standing up. The goals are tabs along the top,
// each with how far it is (in %), the goal the top bar shows chosen; the goal's trail runs down from how far it is through the ideas
// left to do — a step under the ideas it depends on, the ones that can go at once side by side (two at most, the rest a tap away) —
// to its flag, raised when its leader accepts it against its metrics. An idea at work shows its tasks left with the heads of the
// agents who do them, in their waves; a stop that waits for the person is a gate. What is done is not on the trail (Done shows it).
// A tap opens the idea's screen, as from the Board; *new* marks what changed since the Map was last shown on this phone.
import { h, icon } from "./util.js";
import { keepGoal } from "./shell-top.js";
import { rowState } from "./shell-ideas.js";
import { goalState } from "./shell-goal.js";
import { PRIORITY_WORDS, hhmm } from "./shell-words.js";
import { whoHead } from "./shell-who.js";

export const MAP_VIEW = "map";

const NEEDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed" };
const seenKey = (project) => `orkboard.map.seen.${project || ""}`;

/** "18:00" from a bare "HH:MM" or an ISO time. */
const until = (u) => (/^\d{1,2}:\d{2}$/.test(String(u || "")) ? u : hhmm(u));

/** Why a node that is not done does not move, in words (the Map's own words: §4.3's, as the Agents' chips). "" when it moves. */
export function waitsWords(node) {
  const w = node.waits;
  if (!w || node.state === "done") return "";
  const at = until(w.until);
  if (w.kind === "you") return NEEDS[node.needs_you] || "needs you";
  if (w.kind === "idea") return `waits for ${w.title || w.ref}`;
  if (w.kind === "files") return `same files as ${w.title || w.ref}`;
  if (w.kind === "limits") return at ? `waits for limits · after ${at}` : "waits for limits";
  if (w.kind === "reserve") return at ? `keeps your reserve · after ${at}` : "keeps your reserve";
  if (w.kind === "night") return "tonight";
  if (w.kind === "stopped") return "stopped";
  return "";
}

/** `core`: the board's frame; `goalSheet`: New goal. Returns {section(), enter()}. */
export function makeMap(core, goalSheet) {
  const st = core.st;
  let since = 0;                                        // the time the Map was last shown before this time (ms); 0: never, nothing is new

  /** The Map is shown now: what changed after the last time is *new* until the next time. */
  function enter() {
    const key = seenKey(st.snap?.project);
    let prev = 0;
    try { prev = Number(localStorage.getItem(key)) || 0; localStorage.setItem(key, String(Date.now())); } catch { /* the Map works without it */ }
    since = prev;
  }

  const LANES = 2;                                      // stops side by side in a step, before "+N more"
  const wide = new Set();                               // the goals whose steps show every stop side by side

  /** How far a goal is, in %: its ideas done, and the share of the tasks done of each idea at work. */
  function progressOf(mine) {
    if (!mine.length) return 0;
    const done = mine.filter((n) => n.state === "done").length;
    const part = mine.filter((n) => n.state !== "done" && n.progress?.total > 0).reduce((s, n) => s + n.progress.done / n.progress.total, 0);
    return Math.round(((done + part) / mine.length) * 100);
  }

  /** A task's waves: a task is in the wave after the deepest it follows. */
  function wavesOf(tasks) {
    const wave = {};
    const of = (t, seen = new Set()) => {
      if (wave[t.id]) return wave[t.id];
      if (seen.has(t.id)) return 1;
      seen.add(t.id);
      const deps = (t.after || []).map((id) => tasks.find((x) => x.id === id)).filter(Boolean);
      return (wave[t.id] = 1 + Math.max(0, ...deps.map((d) => of(d, seen))));
    };
    tasks.forEach((t) => of(t));
    const out = [];
    for (const t of tasks) (out[wave[t.id] - 1] ||= []).push(t);
    return out.filter(Boolean);
  }

  const TASK_WORDS = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "at Review", failed: "needs you", held: "held" };
  function tasksLeft(node) {
    const left = (node.tasks || []).filter((t) => t.state !== "merged" && t.state !== "dropped");
    if (!left.length || node.state === "done") return null;
    const done = node.tasks.length - left.length;
    return h("div", { class: "map-tasks", "aria-label": `Tasks of ${node.title}` },
      ...wavesOf(left).map((wave, i) => h("div", { class: "map-wave", "data-wave": String(i + 1) },
        ...wave.map((t) => h("button", { class: "map-task", type: "button", "data-state": t.state,
          onclick: () => core.open({ kind: "task", slug: node.slug, task: t.id }, "map") },
          t.head ? whoHead(t.head, true) : null, h("span", { class: "map-task-title" }, t.title), h("small", {}, TASK_WORDS[t.state] || t.state))))),
      done ? h("small", { class: "muted map-tasks-done" }, `${done} done`) : null);
  }

  /** "checks 1/2": how many of the checks that apply to an idea passed. */
  function checksMark(checks) {
    const on = (checks || []).filter((c) => c.applies);
    if (!on.length) return null;
    const passed = on.filter((c) => c.state === "passed").length;
    return h("span", { class: `map-mark map-checks${passed === on.length ? " is-passed" : ""}`,
      "aria-label": `Checks: ${passed} of ${on.length} passed: ${on.map((c) => c.name).join(", ")}` }, `checks ${passed}/${on.length}`);
  }

  /** A goal's team: its agents' heads, then their names, the checkers' marked. */
  /** The goal's party: its leader, then its builders and checkers (a checker says so). */
  function teamLine(team, leader) {
    if (!(team || []).length && !leader) return null;
    const words = (team || []).map((t) => `${t.name}${t.every ? " (checks every idea)" : t.checks ? " (checks)" : ""}`).join(", ");
    return h("p", { class: "map-team muted" }, h("span", { class: "team-mark-heads" }, ...[leader, ...(team || [])].filter(Boolean).map((t) => whoHead(t.head, true))),
      leader ? ` Led by ${leader.name}${words ? ` · ${words}` : ""}` : ` Team: ${words}`);
  }

  function row(node, titleOf) {
    const s = rowState(node, titleOf);
    const why = waitsWords(node);
    const needsHand = node.needs_you && node.state !== "done";
    const isNew = since && node.updated && Date.parse(node.updated) > since;
    return h("li", { class: `map-row state-${node.state}${needsHand ? " needs-hand" : ""}${node.waits && !needsHand ? " is-waiting" : ""}${node.state === "proposed" ? " is-proposed" : ""}`,
      "data-slug": node.slug },
      needsHand ? h("span", { class: "trail-gate" }, icon("warning-diamond"), " Waits for you") : null,
      h("button", { class: "map-open", type: "button", onclick: () => core.open({ kind: "idea", slug: node.slug }, "map") },
        h("span", { class: "idea-title" }, node.title),
        h("span", { class: "idea-meta" },
          needsHand ? h("span", { class: "map-hand", title: "Needs your hand" }, "●") : null,
          h("span", { class: `state-word ${s.cls}` }, s.spin ? h("span", { class: "spin", "aria-hidden": "true" }, "↻") : null, s.spin ? " " : null, s.text),
          why && why !== s.text && !s.text.includes(why) ? h("span", { class: "map-why" }, why) : null,
          node.by_itself ? h("span", { class: "map-mark" }, "by itself") : null,
          node.estimate ? h("span", { class: "map-mark" }, `≈$${node.estimate.usd_low.toFixed(2)}–${node.estimate.usd_high.toFixed(2)}`) : null,
          isNew ? h("span", { class: "map-new" }, "new") : null,
          checksMark(node.checks))),
      tasksLeft(node));
  }

  /** The goal's steps: its ideas left by tier, top to bottom, the ones of a tier side by side. */
  function steps(open) {
    const by = new Map();
    for (const n of open) by.set(n.tier || 1, [...(by.get(n.tier || 1) || []), n]);
    return [...by.keys()].sort((a, b) => a - b).map((t) => by.get(t).sort((a, b) => (a.needs_you ? 0 : 1) - (b.needs_you ? 0 : 1)));
  }

  function goalSection(goal, nodes, titleOf) {
    const mine = nodes.filter((n) => n.goal === goal.slug);
    const open = mine.filter((n) => n.state !== "done"), done = mine.filter((n) => n.state === "done");
    const money = goal.usd == null ? "—" : `≈$${Math.round(goal.usd)} so far`;
    const pct = progressOf(mine);
    const all = wide.has(goal.slug);
    const flag = goal.verdict ? (goal.verdict.met ? "is-met" : "is-not") : "";
    const flagWords = goal.verdict ? (goal.verdict.met ? `Met · ${goal.verdict.by}` : `Not met yet · ${goal.verdict.by}`) : open.length ? "The goal" : "Its ideas are done";
    return h("section", { class: "map-goal", "data-goal": goal.slug, "aria-label": goal.title },        // its title: its tab's
      h("p", { class: "map-goal-meta" }, h("span", { class: `prio prio-${goal.priority}` }, PRIORITY_WORDS[goal.priority] || "Normal"),
        goalState(goal) ? h("span", { class: `state-word ${goal.state === "reading" ? "work" : goal.state}` }, goalState(goal)) : null,
        h("span", {}, money)),
      teamLine(goal.team, goal.leader),
      (goal.done_when || []).length ? h("details", { class: "map-done-when" }, h("summary", {}, `Done when · ${goal.done_when[0]}`),
        h("ul", {}, ...goal.done_when.map((l) => h("li", {}, l)))) : null,
      h("div", { class: "trail-v" },
        h("div", { class: "trail-start" }, h("b", { class: "trail-pct", "aria-label": `${pct} % of the way` }, `${pct} %`),
          h("span", { class: "muted" }, `${done.length} of ${mine.length} ideas`)),
        open.length ? h("ol", { class: "trail-steps" }, ...steps(open).map((step) => h("li", { class: "trail-step", "data-tier": String(step[0].tier || 1) },
          h("ul", { class: `trail-lanes${all || step.length < 2 ? "" : " is-two"}` }, ...(all ? step : step.slice(0, LANES)).map((n) => row(n, titleOf))),
          step.length > LANES ? h("button", { class: "linkish trail-more", type: "button", onclick: () => { if (all) wide.delete(goal.slug); else wide.add(goal.slug); core.draw(); } },
            all ? "Fewer side by side" : `+${step.length - LANES} more side by side`) : null)))
          : h("p", { class: "muted trail-empty" }, "No idea left on the way."),
        h("div", { class: `trail-end ${flag}`, "aria-label": `The flag: ${flagWords}` }, h("span", { class: "trail-flag" }, icon("flag")), h("span", {}, flagWords))),
      done.length ? h("details", { class: "done-ideas" }, h("summary", {}, `Done (${done.length})`),
        h("ol", { class: "ideas map-ideas" }, ...done.map((n) => row(n, titleOf)))) : null);
  }

  /** The goals as tabs along the top, each with how far it is; a tap shows its trail (and is the goal the Board shows). */
  function tabs(goals, nodes, on) {
    return h("nav", { class: "map-goal-tabs", role: "tablist", "aria-label": "Goals" }, ...goals.map((g) => {
      const pct = progressOf(nodes.filter((n) => n.goal === g.slug));
      return h("button", { class: `map-goal-tab${g.slug === on ? " is-on" : ""}`, type: "button", role: "tab", "aria-selected": String(g.slug === on),
        "data-goal": g.slug, onclick: () => {
          if ((st.board?.tracks || []).some((t) => t.slug === g.slug)) {        // the Board's goal too, as the top bar's
            st.track = g.slug; st.mapGoal = ""; keepGoal(st.snap?.project, g.slug);
          } else st.mapGoal = g.slug;
          core.draw();
        } },
        h("span", { class: "map-goal-tab-title" }, g.title), h("small", {}, g.verdict?.met ? "met" : `${pct} %`),
        h("i", { class: "map-goal-tab-bar", "aria-hidden": "true" }, h("i", { class: `map-goal-tab-fill p${Math.round(pct / 10) * 10}` })));
    }));
  }

  /** The Map's nodes for the Board tab: the goals' tabs and the chosen one's trail, or why there is none. */
  function section() {
    if (st.mapError) return [h("p", { class: "muted" }, st.mapError)];
    if (!st.map) return [h("p", { class: "muted" }, "Loading…")];
    const goals = st.map.goals;
    if (!st.map.goals.length) {
      return [h("p", { class: "muted" }, "No goals yet."), h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open() }, "New goal")];
    }
    const titles = new Map(st.map.nodes.map((n) => [n.slug, n.title]));
    const titleOf = (slug) => titles.get(slug) || slug;
    const on = goals.find((g) => g.slug === st.mapGoal) || goals.find((g) => g.slug === st.track) || goals[0];
    return [tabs(goals, st.map.nodes, on.slug), goalSection(on, st.map.nodes, titleOf)];
  }

  return { section, enter };
}
