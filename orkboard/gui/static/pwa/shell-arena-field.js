// The field of the party's window (docs/specs/49-one-window.md §5, §10.5, §11; spec 50 §3.4, §3.5, §6.5, §6.6): under the stage switch the party's members (a small framed row: the head wearing three
// signs, three short lines) and, running down from each toward the bottom row, its open tasks in **rows by phase** — *now* (a task at its goal's current wave), *next*, *later* — and in each row one
// **stack** per goal: the front card (132 × 185, its goal's element top left), one or two edges behind it and *×n*; at the far end *✓ k in dev*. A press on a stack of one opens it, on a stack of more
// spreads it (shell-spread.js). A tap on a member shows only its work under the row, two cards to a row from the top. The filter (the goals picked in the Goals sheet) leaves only their stacks.
// Motion says what changed (shell-motion.js): a stack that was not there rises into its column, one that left (merged ✓, dropped ✗, or put away by the filter, with no sign) fades where it stood and
// its column settles, one that moved slides to its new place, a merge's numbers are lit once; none under reduced motion, on the first read of a goal, for what changed while the page was hidden, nor
// under a finger or the focus.
import { h } from "./util.js";
import { midHead, mark } from "./shell-who.js";
import { sign } from "./shell-marks.js";
import { PHASES, rowsOf } from "./shell-phases.js";
import { deckNode } from "./shell-decks.js";
import { makeSpread } from "./shell-spread.js";
import { motionOn, measure, play, settle, pulse, makeHolds } from "./shell-motion.js";

const GHOSTS = 3;                                    // stacks that leave with the animation in one refresh; the rest simply go
const GHOST_MS = 300;                                // a leaving stack fades where it stood this long
const COL_PX = 116, GAP_PX = 6, SIDE_PX = 24;       // a member's column (three fit across at 390 px), the gap between, both sides of the field
const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** `core`: the board's frame (open, st, draw); `hooks`: {process()}. Returns {el, draw(model, ui, bands)}. */
export function makeField(core, hooks) {
  const st = core.st;
  const el = h("div", { class: "boardwrap" });
  const spread = makeSpread(core);
  let seen = new Map(), seenTasks = new Set(), seenGoal = "";   // the stacks on the field at the last draw (`member|key` → {member, phase, index, stack}) and their tasks, for what appears and what leaves
  let seenBase = "";                                 // what the person had picked at the last draw (the party, the stage, the member): a pick moves things by itself, not by what changed
  let merged = new Map();                            // each member's merged tasks at the last draw (the reward)
  const ghosts = new Map();                          // `member|key` → {member, phase, index, at, stack, sign}: stacks that left, standing where they stood while they fade
  const scrolled = new Map();                        // a column's scroll, kept across a draw
  const holds = makeHolds(el, () => { st.tick = (st.tick || 0) + 1; core.draw(); });

  // -- a stack, a Planning goal ------------------------------------------------------------------------------------------------------------------------
  function press(m, stack, origin) {
    if (stack.n === 1) { core.open(stack.top.open, "map"); return; }
    spread.open({ key: `${m.slug}|${stack.key}`, member: m.name, ideaTitle: stack.top.ideaTitle, items: stack.items, origin }, el);
  }
  const stackLabel = (m, s) => (s.n === 1 ? s.top.label : `${s.top.ideaTitle}: ${plural(s.n, "task")} of ${m.name}, ${s.phase}. A tap lays them out in a row`);
  const deck = (m, s, extra = {}) => deckNode(s, { press: (stack) => press(m, stack, el.querySelector(`[data-key="${CSS.escape(s.key)}"]`)), label: stackLabel(m, s), drawn: s.drawn, ...extra });

  /** A row by phase: its word over its left edge and its stacks; `wrap`: two to a row, centred (a member's solo). */
  function phaseRow(phase, nodes, wrap) {
    return h("div", { class: `phase is-${phase}${wrap ? " is-wrap" : ""}`, "data-phase": phase }, h("span", { class: "phase__lbl" }, phase), ...nodes);
  }

  // -- a member: a small framed row, its head wearing three signs (the tool's mark bottom-left, the level's top-right, its state bottom-right), three short lines ---------------
  function memberCard(m, ui) {
    const on = ui.focus === m.slug;
    const port = h("span", { class: "tport" }, midHead(m.head), m.marks.harness ? mark(`harness-${m.marks.harness.id}`, m.marks.harness.tip, "mark--h") : null,
      m.marks.rank ? mark(`rank-${m.marks.rank.n}`, m.marks.rank.tip, "mark--r") : null,
      m.sign ? h("span", { class: `sign ${m.sign.cls}`.trim(), title: m.words }, sign(m.sign.name)) : null);
    const body = h("span", { class: "tbody" }, h("span", { class: "token__name" }, m.name), h("span", { class: "tnum", title: m.runsTip }, m.runs),
      h("span", { class: "tnum muted", title: m.priceTip }, m.price));
    const label = [m.name, m.kit, m.marks.harness?.tip, m.words, m.runsTip, `${m.price} a run`].filter(Boolean).join(", ");
    return h("button", { class: `token${on ? " is-on" : ""}${ui.focus && !on ? " is-dim" : ""}`, type: "button", "aria-pressed": String(on), "data-member": m.slug,
      "aria-label": `${label}. A tap shows only its work.`, onclick: () => { st.focus = on ? "" : m.slug; core.draw(); } }, port, body);
  }

  // -- what a member shows: its open tasks of the picked goals, in rows by phase ----------------------------------------------------------------------------
  const keep = (ui, idea) => !ui.picks.length || ui.picks.includes(idea);
  const rowsFor = (model, m, ui) => rowsOf(m.tasks.filter((t) => keep(ui, t.idea)), model.nodes.map((n) => n.slug));
  const mergedOf = (model, m) => (model.nodes || []).reduce((k, n) => k + (n.tasks || []).filter((t) => t.by?.slug === m.slug && t.state === "merged").length, 0);

  const column = (label, kids, cls, key) => h("div", { class: `stack ${cls}`.trim(), role: "group", "aria-label": label, "data-column": key || null }, ...kids);

  function planningColumn(model, ui) {
    const lead = model.lead, p = model.process;
    const power = h("button", { class: "pwr", type: "button", disabled: !p.next, "data-act": "process", onclick: () => hooks.process(),
      title: p.next ? `${p.lead?.name || "Taskmaster"} reads “${p.next.title}” now` : "No new goal to read" },
    h("b", {}, "Process now"), h("span", { class: "cap" }, p.next ? plural(p.n, "new goal") : "no new goal"));
    const items = model.planning.filter((it) => keep(ui, it.idea));
    const cards = items.map((it) => deckNode({ key: it.key, idea: it.idea, phase: "", items: [it], top: it, n: 1 }, { planning: true, press: () => core.open(it.open, "map"), label: it.label }));
    const kids = [power, cards.length ? phaseRow("planning", cards, true) : h("span", { class: "stack__empty" }, ui.picks.length && model.planning.length ? "Nothing of these goals" : "Nothing in Planning. A new goal starts here.")];
    return column(`${lead?.name || "Taskmaster"}: Planning`, kids, ui.focus === lead?.slug ? "is-col" : "", lead?.slug);
  }

  function memberColumn(model, m, ui, rows) {
    const rowNodes = PHASES.map((phase) => {
      const row = rows.find((r) => r.phase === phase);
      const nodes = (row ? row.stacks : []).map((s) => deck(m, s));
      for (const g of [...ghosts.values()].filter((x) => x.member === m.slug && x.phase === phase).sort((a, b) => a.index - b.index)) {
        const node = deckNode(g.stack, { ghost: { sign: g.sign } });
        node.style.animationDelay = `${-Math.min(GHOST_MS, Date.now() - g.at)}ms`;       // a draw in the middle of the fade goes on from where it was
        nodes.splice(Math.min(g.index, nodes.length), 0, node);
      }
      return nodes.length ? phaseRow(phase, nodes, false) : null;
    }).filter(Boolean);
    const k = mergedOf(model, m);
    const empty = h("span", { class: "stack__empty" }, ui.picks.length && m.tasks.length ? "Nothing of these goals" : "No task now");
    return column(`${m.name}: the task at work is nearest the agent, at the top`, [...(rowNodes.length ? rowNodes : [empty]),
      k ? h("span", { class: "stack__done" }, sign("check"), ` ${k} in dev`) : null], ui.focus === m.slug ? "is-col" : "", m.slug);
  }

  // -- what appears and what leaves ---------------------------------------------------------------------------------------------------------------------------
  /** Called once for each draw of a party's field: marks the stacks whose tasks were not there a moment ago, keeps the ones that left standing for a moment, and says which members merged a
   *  task. `rows`: each member's rows (after the filter); `quiet`: nothing moves (reduced motion, a hidden page). Returns {rewarded, cur}. */
  function observe(model, members, rows, ui, quiet) {
    const goal = model.goal.slug, cur = new Map(), curTasks = new Set(), rewarded = new Set();
    for (const m of members) for (const r of rows.get(m.slug)) r.stacks.forEach((s, index) => { cur.set(`${m.slug}|${s.key}`, { member: m.slug, phase: r.phase, index, stack: s }); s.items.forEach((t) => curTasks.add(t.key)); });
    const still = !quiet && seenGoal === goal;                    // the first read of a goal is not a change
    const state = new Map();                                       // a task's state now, by key
    for (const n of model.nodes) for (const t of n.tasks || []) state.set(`${n.slug}/${t.id}`, t.state);
    let leaving = 0;
    if (still) {
      for (const [key, info] of cur) if (!seen.has(key) && info.stack.items.some((t) => !seenTasks.has(t.key))) info.stack.drawn = true;
      for (const [key, info] of seen) {
        if (cur.has(key) || ghosts.has(key)) continue;
        const states = info.stack.items.map((t) => state.get(t.key));
        const gone = states.every((x) => x === "merged" || x === "dropped"), putAway = !gone && !keep(ui, info.stack.idea) && states.some((x) => x && x !== "merged" && x !== "dropped");
        if ((gone || putAway) && ++leaving <= GHOSTS) {
          ghosts.set(key, { member: info.member, phase: info.phase, index: info.index, at: Date.now(), stack: info.stack,
            sign: gone ? (states.includes("dropped") ? "cross" : "check") : "" });
        }
      }
      for (const m of members) if (mergedOf(model, m) > (merged.get(m.slug) ?? Infinity)) rewarded.add(m.slug);
    }
    seen = cur;
    seenTasks = curTasks;
    seenGoal = goal;
    merged = new Map(members.map((m) => [m.slug, mergedOf(model, m)]));
    if (ghosts.size) setTimeout(clear, GHOST_MS + 20);
    return { rewarded, cur };
  }

  /** The stacks that left and have faded are taken out together and what they held up settles into the gap, unless the column is under a finger or the focus. */
  function clear() {
    const gone = [];
    for (const [key, g] of [...ghosts]) {
      if (Date.now() - g.at < GHOST_MS) continue;
      const node = [...el.querySelectorAll("[data-ghost]")].find((n) => `${g.member}|${n.dataset.ghost}` === key);
      const col = node?.closest(".stack[data-column]");
      if (col && holds.held(col)) { setTimeout(clear, 250); continue; }
      if (node) gone.push(node);
      ghosts.delete(key);
    }
    if (gone.length) settle(gone);
    if ([...el.querySelectorAll(".stack[data-column]")].some((c) => !c.querySelector(".deck, .stack__empty, .pwr"))) { st.tick = (st.tick || 0) + 1; core.draw(); }      // a column left with nothing says so
  }

  // -- the solo: one member's work over the field ---------------------------------------------------------------------------------------------------------
  function solo(model, m, ui) {
    const lead = m.band === "lead";
    const items = lead ? model.planning.filter((it) => keep(ui, it.idea)) : [];
    const rows = lead ? [] : rowsFor(model, m, ui);
    const n = lead ? items.length : rows.reduce((k, r) => k + r.stacks.reduce((j, s) => j + s.n, 0), 0);
    const title = `Only ${m.name}${lead ? "’s work" : "’s tasks"}`;
    const body = lead ? (items.length ? [phaseRow("planning", items.map((it) => deckNode({ key: it.key, idea: it.idea, phase: "", items: [it], top: it, n: 1 }, { planning: true,
      press: () => core.open(it.open, "map"), label: it.label })), true)] : [])
      : rows.map((r) => phaseRow(r.phase, r.stacks.map((s) => deck(m, s)), true));
    const none = lead ? "Nothing in Planning." : ui.picks.length && m.tasks.length ? "Nothing of these goals" : `${m.name} has no task on this party now.`;
    return h("div", { class: "solo", role: "group", "aria-label": title },
      h("div", { class: "solo__head" }, h("h2", { class: "solo__title" }, title), h("span", { class: "ork-count" }, String(n)), h("span", { class: "spacer" }),
        h("button", { class: "ork-btn quiet", type: "button", "data-act": "everyone", onclick: () => { st.focus = ""; core.draw(); } }, "Everyone")),
      h("div", { class: "solo__card" }, h("span", { class: "ork-gem", title: m.priceTip }, `${m.price} a run`),
        h("div", { class: "solo__info" }, h("span", {}, h("b", {}, m.name), h("span", { class: "muted" }, ` · ${m.kit}`)),
          h("span", { class: "cap" }, h("b", {}, m.kw), ` ${m.rule}`), h("span", { class: "cap" }, `${m.runs} ${m.runsWord}`))),
      h("div", { class: "solo__body" }, ...(body.length ? body : [h("p", { class: "cap solo__empty" }, none)])));
  }

  return {
    el,
    /** `model`: shell-arena-words.js `modelOf`; `ui`: {band, focus, picks}; `bands`: the stage switch's node. */
    draw(model, ui, bands) {
      holds.begin();                                                         // what the last draw held back is not waiting any more
      const quiet = !motionOn();
      const base = `${model.goal.slug}|${ui.band}|${ui.focus}`;
      const sameUi = base === seenBase;                                      // a pick of the person's (a stage, a member) moves things by itself: only what changed slides
      const before = !quiet && sameUi ? measure(el) : null;
      const old = new Map([...el.querySelectorAll(".stack[data-column]")].map((s) => [s.dataset.column, s]));
      for (const [key, s] of old) scrolled.set(key, s.scrollTop);
      const left = el.querySelector(".arena-scroll")?.scrollLeft || 0;
      const shown = ui.band === "lead" ? [model.lead].filter(Boolean) : ui.band === "build" ? model.build : model.check;
      const members = [...model.build, ...model.check];
      const rows = new Map(members.map((m) => [m.slug, rowsFor(model, m, ui)]));
      const { rewarded, cur } = observe(model, members, rows, ui, quiet);
      seenBase = base;
      const held = new Set();
      const cols = shown.map((m) => {
        const was = old.get(m.slug);
        if (was && sameUi && holds.held(was)) { held.add(m.slug); return was; }   // under a finger or the focus: it waits
        return m.band === "lead" ? planningColumn(model, ui) : memberColumn(model, m, ui, rows.get(m.slug));
      });
      const tpl = shown.map(() => "minmax(0, 1fr)");
      const wide = shown.length * COL_PX + GAP_PX * Math.max(0, shown.length - 1) + SIDE_PX;
      const grid = h("div", { class: "cgrid" }, ...cols);
      const row = h("div", { class: "tokens" }, ...shown.map((m) => memberCard(m, ui)));
      grid.style.setProperty("--cols", tpl.join(" "));
      row.style.setProperty("--cols", tpl.join(" "));
      const inner = h("div", { class: "arena__in" }, row, grid);
      inner.style.minWidth = `${wide}px`;
      const wrap = h("div", { class: "arena-scroll" }, inner);
      const focus = shown.find((m) => m.slug === ui.focus);
      spread.still((key) => cur.has(key));                                   // a spread whose stack is gone closes itself
      el.replaceChildren(...[bands, wrap, focus ? solo(model, focus, ui) : null, spread.node()].filter(Boolean));
      for (const s of el.querySelectorAll(".stack")) { const top = scrolled.get(s.dataset.column || ""); if (top && !held.has(s.dataset.column)) s.scrollTop = top; }
      el.querySelector(".arena-scroll").scrollLeft = left;
      for (const slug of rewarded) {                  // the quiet reward: the member's first number and its column's count, once
        pulse(el.querySelector(`.token[data-member="${slug}"] .tnum`));
        if (!held.has(slug)) pulse(el.querySelector(`.stack[data-column="${slug}"] .stack__done`));
      }
      if (before) play(el, before);
    },
  };
}
