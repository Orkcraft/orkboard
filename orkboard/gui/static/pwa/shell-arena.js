// The party's window on the phone (docs/specs/49-one-window.md §10, spec 50 §6, spec 52 §5; decisions §62, §63, §65): the Board is one screen with no tab bar. Under the top bar: the goals bar
// (*⌄ Tech · 3 of 12 goals done*, the Goals sheet and the filter: shell-goals.js; at its right the gate, quiet: shell-party.js), the flag line after a gate's merge, the stage switch and the field of that
// stage (shell-arena-field.js). The stage switch wears the party's faces side by side: each tab its band's heads over its word, no number, one sign (✗ a failure, else ! a stop) on the face it comes
// from; the faces of the tab shown are the members (a tap shows only its tasks: spec 53 §1). The party's deck stands at the goals bar's left (shell-where.js), whose sheet picks the party or Operations. What waits for you lies along the bottom (shell-stops.js). Operations takes the
// field's place when the parties' sheet picks it (the deck then stands at its head). The words and the lists are shell-arena-words.js's; this module draws them and keeps what the person picked (`st.track`, `st.view`, `st.band`, `st.focus`, `st.picks`).
import { h, head as raceHead } from "./util.js";
import { sign } from "./shell-marks.js";
import { steady } from "./shell-util.js";
import { keepGoal, keptGoal } from "./shell-top.js";
import { OPS_VIEW } from "./shell-ops.js";
import { modelOf, shownGoal, doneWords } from "./shell-arena-words.js";
import { makeParty } from "./shell-party.js";
import { makeGoals } from "./shell-goals.js";
import { makeField } from "./shell-arena-field.js";
import { keepFocus, pointerGuard } from "./shell-motion.js";

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
  const goals = makeGoals(core, (slug) => party.open(slug));  // the goals bar, the Goals sheet and the filter (shell-goals.js)
  const guard = pointerGuard([el, ...party.sheets, ...goals.sheets], () => api.draw());   // no lost tap: a draw waits while a pointer is down (spec 50 §6.9)
  let current = null;                                         // the model of the party shown, for the field's hooks
  const field = makeField(core, {
    process: () => current && process(current),
  });

  // -- the stage switch: three tabs, the band's faces side by side over its word (no number); the faces of the tab shown are the members ---------------------------------------
  const faceHead = (x) => (x.head ? raceHead(x.head.race, x.head.tier) : h("span", { class: "band__nohead" }));
  const faceSign = (x) => (x.sign ? h("span", { class: `band__sign ${x.sign === "cross" ? "danger" : "alert"}`, "data-sign": x.sign }, sign(x.sign)) : null);
  /** A face of the tab shown: a button (a tap shows only that member's tasks, again everyone). */
  function face(x) {
    const on = st.focus === x.slug, words = `Only ${x.name}${x.lead ? "’s work" : "’s tasks"}`;
    return h("button", { class: `band__face${on ? " is-on" : ""}`, type: "button", "aria-pressed": String(on), "data-member": x.slug, "aria-label": words, title: words,
      onclick: () => { st.focus = on ? "" : x.slug; core.draw(); } }, faceHead(x), faceSign(x));
  }
  function faces(f, pressable) {
    const heads = f.heads.length ? f.heads.map((x) => (pressable ? face(x) : h("span", { class: "band__face", "data-member": x.slug }, faceHead(x), faceSign(x))))
      : [h("span", { class: "band__nohead is-empty" })];
    return h("span", { class: `band__faces${f.heads.length > 3 ? " is-four" : ""}`, ...(pressable ? {} : { "aria-hidden": "true" }) }, ...heads);
  }
  function stageSwitch(m, band) {
    return h("div", { class: "stagebar" }, h("div", { class: "bands", role: "tablist", "aria-label": "Stages" }, ...m.bands.map(([key, name]) => {
      const f = m.faces[key], on = key === band;
      const attrs = { class: `band${on ? " is-on" : ""}`, role: "tab", "aria-selected": String(on), "data-band": key, "data-sign": f.sign || null, "aria-label": f.label };
      return on ? h("div", attrs, faces(f, true), h("span", { class: "band__name" }, name))                      // the tab shown: its faces are buttons, so the tab is not one
        : h("button", { ...attrs, type: "button", onclick: () => { st.band = key; st.focus = ""; core.draw(); } }, faces(f, false), h("span", { class: "band__name" }, name));
    })));
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
      h("button", { class: "ork-btn", type: "button", "aria-haspopup": "dialog", onclick: () => ops.openMenu() }, "New…"), gear, core.partyDeck())), ...ops.section());
  }

  const needsGoal = () => h("div", { class: "arena-empty" }, h("p", { class: "muted" }, "No parties yet."),
    h("div", { class: "row" }, h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open("") }, "New party"), core.partyDeck()));

  /** The party's window drawn: the goals bar with the gate, the flag line and the field (what the person sees of the Board read). */
  function paint() {
    const card = cards.section(st.cards[0]);
    const lead = card ? [card] : [];
    if (!st.board && st.boardError) {                       // no project open: Operations is the person's, so it is offered all the same
      el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, st.boardError), opsView());
      return;
    }
    if (!st.board || (!st.map && !st.mapError)) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, "Loading…")); return; }
    if (st.mapError && !st.map) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, st.mapError)); return; }
    const slug = shownGoal(st, keptGoal(st.snap?.project));
    if (slug && slug !== st.track) st.track = slug;
    const m = st.view === OPS_VIEW ? null : modelOf(st, slug);
    current = m;
    todayOf(slug, m);
    if (st.view === OPS_VIEW) { el.replaceChildren(...lead, opsView()); return; }
    if (!m) { el.replaceChildren(...lead, needsGoal()); return; }
    const band = st.band || m.first;
    const shown = band === "lead" ? [m.lead] : band === "build" ? m.build : m.check;
    if (st.focus && !shown.some((x) => x?.slug === st.focus)) st.focus = "";           // the member shown is not in this stage
    field.draw(m, { band, focus: st.focus, picks: m.picks }, stageSwitch(m, band));
    // The field stays where it is in the page: taking it out and putting it back would reset the scroll of its strip and its columns, which it has just put back as they were.
    for (const kid of [...el.childNodes]) if (kid !== field.el) kid.remove();
    el.prepend(...[...lead, goals.bar(m, party.gate(), core.partyDeck()), party.line(slug)].filter(Boolean));
    if (field.el.parentNode !== el) el.append(field.el);
  }

  const api = {
    el,
    sheets: [...party.sheets, ...goals.sheets],
    /** Pick the party of a stop (a push arrival, a link to Needs you) and show it. */
    show(slug) { if (slug) { st.track = slug; Object.assign(st, { view: "", band: "", focus: "" }); core.draw(); } },
    /** A party picked in the parties' sheet, or Operations. */
    pick: pickGoal,
    pickOps,
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
