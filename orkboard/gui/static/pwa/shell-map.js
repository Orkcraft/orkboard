// The Map on the phone (docs/specs/39-map.md §5): a tree does not fit 390 px, so the same data is a list. Each goal is a section (its
// head, then its ideas in tier order); an idea is a row with its tier as dots, its title, its words (`rowState`, the Board's row), its
// pips, its marks and the ideas it comes after. A tap opens the idea's screen, as from the Board. Done ideas nothing waits on are folded
// at the goal's foot; *new* marks what changed since the Map was last shown on this phone (kept here, for itself). A goal says its team
// (its agents' heads, the checkers' checks: realm/idea_checks.py), an idea how many of its checks passed.
import { h } from "./util.js";
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

  function dots(node, top) {
    const n = Math.max(top, node.tier || 1);
    return h("span", { class: "map-dots", role: "img", "aria-label": `Tier ${node.tier || 1} of ${n}` },
      Array.from({ length: n }, (_, i) => (i + 1 === (node.tier || 1) ? "●" : "○")).join(""));
  }

  function pips(node) {
    const tasks = node.tasks || [];
    if (!tasks.length) return null;
    const merged = tasks.filter((t) => t.state === "merged").length;
    return h("span", { class: "map-pips", role: "img", "aria-label": `${merged} of ${tasks.length} tasks merged` },
      ...tasks.map((t) => h("i", { class: `pip pip-${t.state === "merged" ? "done" : t.state === "running" || t.state === "testing" ? "work" : "wait"}` })));
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

  function row(node, top, titleOf) {
    const s = rowState(node, titleOf);
    const why = waitsWords(node);
    const needsHand = node.needs_you && node.state !== "done";
    const isNew = since && node.updated && Date.parse(node.updated) > since;
    const after = (node.depends_on || []).map(titleOf);
    return h("li", { class: `map-row state-${node.state}${needsHand ? " needs-hand" : ""}${node.waits && !needsHand ? " is-waiting" : ""}${node.state === "proposed" ? " is-proposed" : ""}`,
      "data-slug": node.slug },
      h("button", { class: "map-open", type: "button", onclick: () => core.open({ kind: "idea", slug: node.slug }, "map") },
        h("span", { class: "map-top" }, dots(node, top), h("span", { class: "idea-title" }, node.title)),
        h("span", { class: "idea-meta" },
          needsHand ? h("span", { class: "map-hand", title: "Needs your hand" }, "●") : null,
          h("span", { class: `state-word ${s.cls}` }, s.spin ? h("span", { class: "spin", "aria-hidden": "true" }, "↻") : null, s.spin ? " " : null, s.text),
          why && why !== s.text && !s.text.includes(why) ? h("span", { class: "map-why" }, why) : null,
          node.by_itself ? h("span", { class: "map-mark" }, "by itself") : null,
          node.estimate ? h("span", { class: "map-mark" }, `≈$${node.estimate.usd_low.toFixed(2)}–${node.estimate.usd_high.toFixed(2)}`) : null,
          isNew ? h("span", { class: "map-new" }, "new") : null,
          checksMark(node.checks),
          pips(node)),
        after.length ? h("span", { class: "map-after" }, `after ${after.join(", ")}`) : null));
  }

  function goalSection(goal, nodes, titleOf) {
    const mine = nodes.filter((n) => n.goal === goal.slug);
    const shown = mine.filter((n) => !n.folded).sort((a, b) => (a.tier || 1) - (b.tier || 1) || (a.needs_you ? 0 : 1) - (b.needs_you ? 0 : 1));
    const folded = mine.filter((n) => n.folded);
    const top = Math.max(1, ...mine.map((n) => n.tier || 1));
    const money = goal.usd == null ? "—" : `≈$${Math.round(goal.usd)} so far`;
    return h("section", { class: "map-goal", "data-goal": goal.slug, "aria-label": goal.title },
      h("h3", {}, goal.title),
      h("p", { class: "map-goal-meta" }, h("span", { class: `prio prio-${goal.priority}` }, PRIORITY_WORDS[goal.priority] || "Normal"),
        goalState(goal) ? h("span", { class: `state-word ${goal.state === "reading" ? "work" : goal.state}` }, goalState(goal)) : null,
        h("span", {}, `${goal.done} of ${goal.ideas} done`), h("span", {}, money),
        goal.verdict ? h("span", { class: `verdict-word ${goal.verdict.met ? "is-met" : "is-not"}` }, goal.verdict.met ? `accepted by ${goal.verdict.by}` : `not met, says ${goal.verdict.by}`) : null),
      teamLine(goal.team, goal.leader),
      (goal.done_when || []).length ? h("details", { class: "map-done-when" }, h("summary", {}, `Done when · ${goal.done_when[0]}`),
        h("ul", {}, ...goal.done_when.map((l) => h("li", {}, l)))) : null,
      shown.length ? h("ol", { class: "ideas map-ideas" }, ...shown.map((n) => row(n, top, titleOf))) : h("p", { class: "muted" }, "No ideas in this goal yet."),
      folded.length ? h("details", { class: "done-ideas" }, h("summary", {}, `Done (${folded.length})`),
        h("ol", { class: "ideas map-ideas" }, ...folded.map((n) => row(n, top, titleOf)))) : null);
  }

  /** The Map's nodes for the Board tab: its goals (the chosen one alone), or why there is none. */
  function section() {
    if (st.mapError) return [h("p", { class: "muted" }, st.mapError)];
    if (!st.map) return [h("p", { class: "muted" }, "Loading…")];
    const goals = st.map.goals;                           // every goal: the Map is the view of them all (the Board shows one)
    if (!st.map.goals.length) {
      return [h("p", { class: "muted" }, "No goals yet."), h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open() }, "New goal")];
    }
    const titles = new Map(st.map.nodes.map((n) => [n.slug, n.title]));
    const titleOf = (slug) => titles.get(slug) || slug;
    return goals.map((g) => goalSection(g, st.map.nodes, titleOf));
  }

  return { section, enter };
}
