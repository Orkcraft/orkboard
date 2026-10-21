// The field of the goal's window (docs/specs/49-one-window.md §5, §10.5, §11): under the stage switch the party's members (a small framed row: the head wearing three signs,
// three short lines) and, running down from each toward the bottom row, its open tasks (the top row, against the member, lit, the rows below muted; at the far end *✓ k in
// dev*); a tap on a member shows only its work under the row, three to a row from the top. Motion says what changed (shell-motion.js): a task that was not there rises into its
// column, a task that left (merged ✓, dropped ✗) fades where it stands and its column settles, a task that moved slides to its new place, a merge's numbers are highlighted
// once; none under reduced motion, on the first read of a goal, for what changed while the page was hidden, nor under a finger or the focus.
import { h, icon } from "./util.js";
import { midHead, mark } from "./shell-who.js";
import { motionOn, measure, play, settle, pulse, makeHolds } from "./shell-motion.js";

const GHOSTS = 3;                                    // tasks that leave with the animation in one refresh; the rest simply go
const GHOST_MS = 300;                                // a leaving task fades where it stands this long
const COL_PX = 116, GAP_PX = 6, SIDE_PX = 24;       // a member's column (three fit across at 390 px), the gap between, both sides of the field
const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** `core`: the board's frame (open, st, draw); `hooks`: {process()}. Returns {el, draw(model, ui, bands)}. */
export function makeField(core, hooks) {
  const st = core.st;
  const el = h("div", { class: "boardwrap" });
  let seen = new Map(), seenGoal = "";               // the tasks on the field at the last draw (key → {member, index, item}), for what appears and what leaves
  let seenUi = "";                                   // what the person had picked at the last draw: a pick moves things by itself, not by what changed
  let merged = new Map();                            // each member's merged tasks at the last draw (the reward)
  const ghosts = new Map();                          // key → {member, index, item, at}: tasks that left, standing where they stood while they fade
  const scrolled = new Map();                        // a column's scroll, kept across a draw
  const holds = makeHolds(el, () => { st.tick = (st.tick || 0) + 1; core.draw(); });

  // -- one task, one Planning item -------------------------------------------------------------------------------------------------------------------
  function card(it, { later = false, solo = false, drawn = false, ghost = false, planning = false } = {}) {
    const cls = ["tcard"];
    if (planning) cls.push(it.kind === "stop" ? "is-stop" : it.kind === "busy" ? "is-run" : "is-wait");
    else cls.push({ running: "is-run", testing: "is-run", review: "is-review", ready: "is-next", waiting: "is-wait", held: "is-wait", failed: "is-fail", merged: "is-out", dropped: "is-out" }[it.state] || "");
    if (later) cls.push("is-later");
    if (drawn) cls.push("is-drawn");
    const mk = planning ? "" : it.mark === "clock" ? icon("clock") : it.mark;
    const top = h("span", { class: "tcard__top" }, h("span", { class: "tbadge" }, planning ? it.badge : String(it.wave)), planning ? null : h("span", { class: "tcard__wave" }, "wave"),
      h("span", { class: "tcard__mark" }, mk));
    const kids = [top, solo ? null : h("span", { class: "tcard__idea" }, planning ? "Planning" : it.ideaTitle),
      h("span", { class: "tcard__name" }, it.title), h("span", { class: "tcard__foot" }, it.words)];
    if (ghost) return h("div", { class: `${cls.join(" ")} is-leaving`, "aria-hidden": "true", "data-ghost": it.key, "data-sign": it.mark }, ...kids);
    return h("button", { class: cls.join(" "), type: "button", title: it.tip, "aria-label": it.label, "data-task": planning ? null : it.id, "data-idea": it.idea, "data-key": it.key,
      "data-state": planning ? it.kind : it.state, onclick: () => core.open(it.open, "map") }, ...kids);
  }

  // -- a member: a small framed row, its head wearing three signs (the tool's mark bottom-left, the level's top-right, its state bottom-right), three short lines ---------------
  function memberCard(m, ui) {
    const on = ui.focus === m.slug;
    const port = h("span", { class: "tport" }, midHead(m.head), m.marks.harness ? mark(`harness-${m.marks.harness.id}`, m.marks.harness.tip, "mark--h") : null,
      m.marks.rank ? mark(`rank-${m.marks.rank.n}`, m.marks.rank.tip, "mark--r") : null,
      m.sign ? h("span", { class: `sign ${m.sign.cls}`.trim(), title: m.words }, m.sign.text === "moon" ? icon("moon") : m.sign.text) : null);
    const body = h("span", { class: "tbody" }, h("span", { class: "token__name" }, m.name), h("span", { class: "tnum", title: m.runsTip }, m.runs),
      h("span", { class: "tnum muted", title: m.priceTip }, m.price));
    const label = [m.name, m.kit, m.marks.harness?.tip, m.words, m.runsTip, `${m.price} a run`].filter(Boolean).join(", ");
    return h("button", { class: `token${on ? " is-on" : ""}${ui.focus && !on ? " is-dim" : ""}`, type: "button", "aria-pressed": String(on), "data-member": m.slug,
      "aria-label": `${label}. A tap shows only its work.`, onclick: () => { st.focus = on ? "" : m.slug; core.draw(); } }, port, body);
  }

  // -- the columns ----------------------------------------------------------------------------------------------------------------------------------------
  const stack = (label, kids, cls, key) => h("div", { class: `stack ${cls}`.trim(), role: "group", "aria-label": label, "data-column": key || null }, ...kids);

  function planningStack(model, ui) {
    const lead = model.lead, items = model.planning, p = model.process;
    const power = h("button", { class: "pwr", type: "button", disabled: !p.next, "data-act": "process", onclick: () => hooks.process(),
      title: p.next ? `${p.lead?.name || "Taskmaster"} reads “${p.next.title}” now` : "No new idea to read" },
    h("b", {}, "Process now"), h("span", { class: "cap" }, p.next ? plural(p.n, "new idea") : "no new idea"));
    const kids = [power, ...(items.length ? items.map((it, i) => card(it, { later: i > 0, planning: true })) : [h("span", { class: "stack__empty" }, "Nothing in Planning. A new idea starts here.")])];
    return stack(`${lead?.name || "Taskmaster"}: Planning`, kids, ui.focus === lead?.slug ? "is-col" : "", lead?.slug);
  }

  const mergedOf = (model, m) => (model.nodes || []).reduce((k, n) => k + (n.tasks || []).filter((t) => t.by?.slug === m.slug && t.state === "merged").length, 0);

  function memberStack(model, m, ui) {
    const items = m.tasks.filter((t) => !ui.idea || t.idea === ui.idea);
    const kids = items.map((it, i) => card(it, { later: i > 0, drawn: it.drawn }));
    for (const g of [...ghosts.values()].filter((x) => x.member === m.slug).sort((a, b) => a.index - b.index)) {
      const node = card(g.item, { ghost: true });
      node.style.animationDelay = `${-Math.min(GHOST_MS, Date.now() - g.at)}ms`;       // a draw in the middle of the fade goes on from where it was
      kids.splice(Math.min(g.index, kids.length), 0, node);
    }
    const k = mergedOf(model, m);
    return stack(`${m.name}: the task at work is nearest the agent, at the top`, [...(kids.length ? kids : [h("span", { class: "stack__empty" }, "No task now")]),
      k ? h("span", { class: "stack__done" }, `✓ ${k} in dev`) : null], ui.focus === m.slug ? "is-col" : "", m.slug);
  }

  // -- what appears and what leaves ---------------------------------------------------------------------------------------------------------------------------
  /** Called once for each draw of a goal's field: marks the tasks that were not there a moment ago, keeps the ones that left standing for a moment, and says which
   *  members merged a task. `quiet`: nothing moves (reduced motion, a hidden page). */
  function observe(model, members, quiet) {
    const goal = model.goal.slug, cur = new Map(), rewarded = new Set();
    for (const m of members) m.tasks.forEach((t, index) => cur.set(t.key, { member: m.slug, index, item: t }));
    const still = !quiet && seenGoal === goal;                    // the first read of a goal is not a change
    let leaving = 0;
    if (still) {
      for (const [key, info] of cur) if (!seen.has(key)) info.item.drawn = true;
      for (const [key, info] of seen) {
        if (cur.has(key) || ghosts.has(key)) continue;
        const t = (model.nodes.find((n) => n.slug === info.item.idea)?.tasks || []).find((x) => x.id === info.item.id);
        if ((t?.state === "merged" || t?.state === "dropped") && ++leaving <= GHOSTS) {
          const drop = t.state === "dropped";
          ghosts.set(key, { member: info.member, index: info.index, at: Date.now(), item: { ...info.item, state: t.state, words: drop ? "dropped" : "in dev", mark: drop ? "✗" : "✓", key } });
        }
      }
      for (const m of members) if (mergedOf(model, m) > (merged.get(m.slug) ?? Infinity)) rewarded.add(m.slug);
    }
    seen = cur;
    seenGoal = goal;
    merged = new Map(members.map((m) => [m.slug, mergedOf(model, m)]));
    if (ghosts.size) setTimeout(clear, GHOST_MS + 20);
    return rewarded;
  }

  /** The leaving tasks that have faded are taken out together and what they held up settles into the gap, unless the column is under a finger or the focus. */
  function clear() {
    const gone = [];
    for (const [key, g] of [...ghosts]) {
      if (Date.now() - g.at < GHOST_MS) continue;
      const node = [...el.querySelectorAll("[data-ghost]")].find((n) => n.dataset.ghost === key);
      if (node?.parentElement && holds.held(node.parentElement)) { setTimeout(clear, 250); continue; }
      if (node) gone.push(node);
      ghosts.delete(key);
    }
    if (gone.length) settle(gone);
  }

  // -- the solo: one member's work over the field ---------------------------------------------------------------------------------------------------------
  function solo(model, m, ui) {
    const lead = m.band === "lead";
    const items = (lead ? model.planning : m.tasks).filter((t) => lead || !ui.idea || t.idea === ui.idea);
    const rows = [];
    for (let i = 0; i < items.length; i += 3) rows.push(items.slice(i, i + 3));
    const title = `Only ${m.name}${lead ? "’s work" : "’s tasks"}`;
    const body = rows.length ? rows.map((r, i) => h("div", { class: "srow" }, ...r.map((it) => card(it, { later: i > 0, solo: true, planning: lead }))))
      : [h("p", { class: "cap solo__empty" }, lead ? "Nothing in Planning." : `${m.name} has no task on this goal now.`)];
    return h("div", { class: "solo", role: "group", "aria-label": title },
      h("div", { class: "solo__head" }, h("h2", { class: "solo__title" }, title), h("span", { class: "ork-count" }, String(items.length)), h("span", { class: "spacer" }),
        h("button", { class: "ork-btn quiet", type: "button", "data-act": "everyone", onclick: () => { st.focus = ""; core.draw(); } }, "Everyone")),
      h("div", { class: "solo__card" }, h("span", { class: "ork-gem", title: m.priceTip }, `${m.price} a run`),
        h("div", { class: "solo__info" }, h("span", {}, h("b", {}, m.name), h("span", { class: "muted" }, ` · ${m.kit}`)),
          h("span", { class: "cap" }, h("b", {}, m.kw), ` ${m.rule}`), h("span", { class: "cap" }, `${m.runs} ${m.runsWord}`))),
      h("div", { class: "solo__body" }, ...body));
  }

  return {
    el,
    /** `model`: shell-arena-words.js `modelOf`; `ui`: {band, focus, idea}; `bands`: the stage switch's node. */
    draw(model, ui, bands) {
      holds.begin();                                                         // what the last draw held back is not waiting any more
      const quiet = !motionOn();
      const uiKey = `${model.goal.slug}|${ui.band}|${ui.focus}|${ui.idea}`;
      const sameUi = uiKey === seenUi;                                       // a pick of the person's moves things by itself: only what changed slides
      const before = !quiet && sameUi ? measure(el) : null;
      const old = new Map([...el.querySelectorAll(".stack[data-column]")].map((s) => [s.dataset.column, s]));
      for (const [key, s] of old) scrolled.set(key, s.scrollTop);
      const left = el.querySelector(".arena-scroll")?.scrollLeft || 0;
      const shown = ui.band === "lead" ? [model.lead].filter(Boolean) : ui.band === "build" ? model.build : model.check;
      const rewarded = observe(model, [...model.build, ...model.check], quiet);
      seenUi = uiKey;
      const held = new Set();
      const cols = [...shown.map((m) => {
        const was = old.get(m.slug);
        if (was && sameUi && holds.held(was)) { held.add(m.slug); return was; }   // under a finger or the focus: it waits
        return m.band === "lead" ? planningStack(model, ui) : memberStack(model, m, ui);
      })];
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
      el.replaceChildren(bands, wrap, ...(focus ? [solo(model, focus, ui)] : []));
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
