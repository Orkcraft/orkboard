// The party's window on the phone (docs/specs/49-one-window.md §10, spec 50 §6, decisions §62, §63): the Board is one screen with no tab bar. Under the top bar: the parties as a row of
// chips (the leader's head, the short name, the stops that wait, ↻ while it works; Operations), the party's line (*3/12 done · ≈$2–4 a goal ›*, About this party; the gate, quiet:
// shell-party.js), the flag line after a gate's merge, the goals bar (*⌄ Goals 7 · 3 at work · 3 ask you*, the Goals sheet and the filter: shell-goals.js), the stage switch (Planning ·
// Implementation · Checking) and the field of that stage (shell-arena-field.js). What waits for you lies along the bottom (shell-stops.js). Operations takes the
// field's place from its chip. The words and the lists are shell-arena-words.js's; this module draws them and keeps what the person picked (`st.track`, `st.view`,
// `st.band`, `st.focus`, `st.picks`).
import { h } from "./util.js";
import { steady } from "./shell-util.js";
import { keepGoal, keptGoal } from "./shell-top.js";
import { OPS_VIEW } from "./shell-ops.js";
import { BANDS, chipsOf, modelOf, shownGoal, doneWords } from "./shell-arena-words.js";
import { whoHead } from "./shell-who.js";
import { sign } from "./shell-marks.js";
import { makeParty } from "./shell-party.js";
import { makeGoals } from "./shell-goals.js";
import { makeField } from "./shell-arena-field.js";
import { keepFocus, pointerGuard } from "./shell-motion.js";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** `core`: the board's frame; `ctx`: {flash}; `parts`: {goalSheet, ops, ideas, cards}. Returns {el, sheets, draw()}. */
export function makeArena(core, ctx, parts) {
  const st = core.st;
  const { goalSheet, ops, ideas, cards } = parts;
  const el = h("section", { class: "pane arena", "aria-label": "The party at work" });
  const fresh = steady(el);

  // -- what the person picks ---------------------------------------------------------------------------------------------------------------------------
  function pickGoal(slug) {
    st.track = slug;
    keepGoal(st.snap?.project, slug);
    Object.assign(st, { view: "", band: "", focus: "" });
    core.draw();
    window.scrollTo(0, 0);
  }
  function pickOps() {
    Object.assign(st, { view: OPS_VIEW, focus: "" });
    core.draw();
  }
  async function process(model) {
    const next = model.process.next;
    if (!next) return;
    const r = await core.call("ideas.queue", { slug: next.slug, queue: "now", via: "party" });
    const who = model.process.lead?.name || "Taskmaster";
    if (r) { ctx.flash(`${who === "Taskmaster" ? "The Taskmaster" : who} drafts it now.`); core.refresh(); }
  }

  const party = makeParty(core, ctx);                         // the party's line, its sheet and the flag line (shell-party.js)
  const goals = makeGoals(core);                              // the goals bar, the Goals sheet and the filter (shell-goals.js)
  const guard = pointerGuard([el, ...party.sheets, ...goals.sheets], () => api.draw());   // no lost tap: a draw waits while a pointer is down (spec 50 §6.9)
  let current = null;                                         // the model of the party shown, for the field's hooks
  const field = makeField(core, {
    process: () => current && process(current),
  });

  // -- the parties as chips ----------------------------------------------------------------------------------------------------------------------------
  function chipRow(list, shown) {
    const chip = (c) => {
      const said = `${c.short}${c.stops ? `, ${plural(c.stops, "stop waits", "stops wait")} for you` : ""}${c.working ? ", at work" : ""}`;
      return h("button", { class: `gchip${c.slug === shown ? " is-on" : ""}`, type: "button", "data-goal": c.slug, "aria-pressed": String(c.slug === shown), "aria-label": said,
        title: c.title, onclick: () => pickGoal(c.slug) },
      c.head ? whoHead(c.head, false) : null, h("span", { class: "gchip__name" }, c.short), c.stops ? h("span", { class: "ork-count warning" }, String(c.stops)) : null,
      c.working ? sign("work", "at work") : null);
    };
    const hasOps = st.snap?.ops_rev !== undefined && (!st.ops || (st.ops.templates || []).length || (st.ops.runs || []).length);
    const opStops = (st.board?.needs_you || []).filter((n) => n.kind.startsWith("op")).length;           // what waits in Operations is seen from every party
    return h("nav", { class: "gchips", "aria-label": "Parties" }, ...list.map(chip),
      hasOps ? h("button", { class: `gchip${st.view === OPS_VIEW ? " is-on" : ""}`, type: "button", "data-goal": OPS_VIEW, "aria-pressed": String(st.view === OPS_VIEW),
        "aria-label": `Operations${opStops ? `, ${plural(opStops, "stop waits", "stops wait")} for you` : ""}`, onclick: pickOps },
      h("span", { class: "gchip__name" }, "Operations"), opStops ? h("span", { class: "ork-count warning" }, String(opStops)) : null) : null);
  }

  // -- the stage switch -------------------------------------------------------------------------------------------------------------------------------------
  function stageSwitch(m, band) {
    return h("div", { class: "bands", role: "tablist", "aria-label": "Stages" }, ...BANDS.map(([key, name]) => {
      const n = m.counts[key], w = m.warn[key];
      return h("button", { class: `band${key === band ? " is-on" : ""}`, role: "tab", type: "button", "aria-selected": String(key === band), "data-band": key,
        "aria-label": `${name}: ${n}${w ? `, ${w} ${w === 1 ? "waits" : "wait"} for you` : ""}`, onclick: () => { st.band = key; st.focus = ""; core.draw(); } },
      h("span", { class: "band__name" }, name), h("span", { class: `ork-count${w ? " warning" : ""}` }, String(n)));
    }));
  }

  /** Today's sheet and its button: the events of the goal shown (and the gate's), then its Done ideas. */
  function todayOf(slug, m) {
    const open = (o) => (o.kind === "gate" ? { kind: "gate" } : o.kind === "goal" ? { kind: "goal", slug: o.slug } : { kind: o.kind, slug: o.slug, ...(o.task ? { task: o.task } : {}) });
    core.setToday({
      events: (st.today?.events || []).filter((e) => e.goal === slug || e.goal === "").map((e) => ({ ...e, go: () => e.open && core.open(open(e.open), "today") })),
      done: (m?.done || []).map((n) => ({ slug: n.slug, title: n.short || n.title, words: doneWords(st.gate, n.slug), go: () => core.open({ kind: "idea", slug: n.slug }, "today") })),
    });
  }

  // -- Operations in the field's place ------------------------------------------------------------------------------------------------------------------------
  function opsView() {
    const gear = h("button", { class: "ork-btn gear", type: "button", "aria-haspopup": "dialog", "aria-label": "Operations settings", onclick: () => ops.openGear() }, "Settings");
    return h("div", { class: "ops-view" }, h("div", { class: "pane-head" }, h("h2", {}, "Operations"), h("div", { class: "row" },
      h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…"), gear)), ...ops.section());
  }

  const needsGoal = () => h("div", { class: "arena-empty" }, h("p", { class: "muted" }, "No parties yet."),
    h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open("") }, "New party"));

  /** The party's window drawn: the chips, its line, the flag line, the ideas bar and the field (what the person sees of the Board read). */
  function paint() {
    const card = cards.section(st.cards[0]);
    const lead = card ? [card] : [];
    if (!st.board && st.boardError) {                       // no project open: Operations is the person's, so it is offered all the same
      el.replaceChildren(...lead, chipRow([], ""), h("p", { class: "muted arena-empty" }, st.boardError), opsView());
      return;
    }
    if (!st.board || (!st.map && !st.mapError)) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, "Loading…")); return; }
    if (st.mapError && !st.map) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, st.mapError)); return; }
    const slug = shownGoal(st, keptGoal(st.snap?.project));
    if (slug && slug !== st.track) st.track = slug;
    const list = chipsOf(st);
    const m = st.view === OPS_VIEW ? null : modelOf(st, slug);
    current = m;
    todayOf(slug, m);
    if (st.view === OPS_VIEW) { el.replaceChildren(...lead, chipRow(list, ""), opsView()); return; }
    if (!m) { el.replaceChildren(...lead, chipRow(list, ""), needsGoal()); return; }
    const band = st.band || m.first;
    const shown = band === "lead" ? [m.lead] : band === "build" ? m.build : m.check;
    if (st.focus && !shown.some((x) => x?.slug === st.focus)) st.focus = "";           // the member shown is not in this stage
    field.draw(m, { band, focus: st.focus, picks: m.picks }, stageSwitch(m, band));
    el.replaceChildren(...[...lead, chipRow(list, slug), party.bar(m), party.line(slug), goals.bar(m), field.el].filter(Boolean));
  }

  const api = {
    el,
    sheets: [...party.sheets, ...goals.sheets],
    /** Pick the party of a stop (a push arrival, a link to Needs you) and show it. */
    show(slug) { if (slug) { st.track = slug; Object.assign(st, { view: "", band: "", focus: "" }); core.draw(); } },
    /** The goal shown, from what the Board read and what this phone showed last. */
    goal: () => shownGoal(st, keptGoal(st.snap?.project)),
    draw() {
      if (guard.waits()) return;                                 // a pointer is down: drawn after it comes up, the signature not used up
      party.watch();                                             // flags newer than this phone saw make the flag line (before the signature: it is part of it)
      const signature = JSON.stringify([st.map, st.board, st.agents, st.roles?.seats, st.roles?.library?.length, st.review, st.gate, st.today, st.track, st.view, st.band, st.focus, st.picks,
        st.cards, st.ops, st.boardError, st.mapError, st.snap?.ops_rev, st.prices, st.flagLine, st.tick, Math.floor(Date.now() / 60000)]);
      if (!fresh(signature)) return;
      keepFocus(el, () => { paint(); goals.sync(); });           // drawn again: a keyboard's place stays where it was; an open Goals sheet shows what it drew
    },
  };
  return api;
}
