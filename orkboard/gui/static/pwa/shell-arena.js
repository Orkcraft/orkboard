// The goal's window on the phone (docs/specs/49-one-window.md §10, decisions §62): the Board is one screen with no tab bar. Under the top bar: the goals as a row of
// chips (the short title, how far, the stops that wait, ↻ while its party works; Operations; + New goal), the goal's header (its flag with the ideas left, its title,
// *k ideas left · n % · ≈$ so far*, the gate's button dev → main), the ideas bar (*▾ n · Now: …*, open: the ideas at work and Done), the stage switch (Planning ·
// Implementation · Checking) and the field of that stage (shell-arena-field.js). What waits for you lies along the bottom (shell-stops.js). Operations takes the
// field's place from its chip. The words and the lists are shell-arena-words.js's; this module draws them and keeps what the person picked (`st.track`, `st.view`,
// `st.band`, `st.focus`, `st.idea`, `st.ideasOpen`).
import { h, icon } from "./util.js";
import { steady } from "./shell-util.js";
import { keepGoal, keptGoal } from "./shell-top.js";
import { OPS_VIEW } from "./shell-ops.js";
import { BANDS, chipsOf, modelOf, shownGoal, doneWords } from "./shell-arena-words.js";
import { makeField } from "./shell-arena-field.js";
import { tallyWords } from "./shell-map.js";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const money = (usd) => (usd == null ? "—" : `≈$${Math.round(usd)} so far`);

/** `core`: the board's frame; `ctx`: {flash}; `parts`: {goalSheet, ops, ideas, cards, flags}. Returns {el, sheets, draw()}. */
export function makeArena(core, ctx, parts) {
  const st = core.st;
  const { goalSheet, ops, ideas, cards, flags } = parts;
  const el = h("section", { class: "pane arena", "aria-label": "The goal at work" });
  const fresh = steady(el);

  // -- what the person picks ---------------------------------------------------------------------------------------------------------------------------
  function pickGoal(slug) {
    st.track = slug;
    keepGoal(st.snap?.project, slug);
    Object.assign(st, { view: "", band: "", focus: "", idea: "", ideasOpen: false });
    core.draw();
    window.scrollTo(0, 0);
  }
  function pickOps() {
    Object.assign(st, { view: OPS_VIEW, focus: "", idea: "", ideasOpen: false });
    core.draw();
  }
  async function editParty(slug) {
    const got = await core.call("ideas.goal", { slug });
    if (got) core.editTeam(got);
  }
  async function process(model) {
    const next = model.process.next;
    if (!next) return;
    const r = await core.call("ideas.queue", { slug: next.slug, queue: "now", via: "party" });
    const who = model.process.lead?.name || "Taskmaster";
    if (r) { ctx.flash(`${who === "Taskmaster" ? "The Taskmaster" : who} drafts it now.`); core.refresh(); }
  }

  let current = null;                                         // the model of the goal shown, for the field's hooks
  const field = makeField(core, {
    process: () => current && process(current),
    seat: () => editParty(st.track),
  });

  // -- the goals as chips ------------------------------------------------------------------------------------------------------------------------------
  function chipRow(list, shown) {
    const chip = (c) => {
      const said = `${c.short}, ${c.pct} %${c.stops ? `, ${plural(c.stops, "stop waits", "stops wait")} for you` : ""}${c.working ? ", at work" : ""}`;
      return h("button", { class: `gchip${c.slug === shown ? " is-on" : ""}`, type: "button", "data-goal": c.slug, "aria-pressed": String(c.slug === shown), "aria-label": said,
        title: `${c.title} · ${c.pct} % of the way`, onclick: () => pickGoal(c.slug) },
      h("span", { class: "gchip__name" }, c.short), h("b", {}, `${c.pct} %`), c.stops ? h("span", { class: "ork-count warning" }, String(c.stops)) : null,
      c.working ? h("span", { class: "muted", "aria-hidden": "true" }, "↻") : null);
    };
    const hasOps = st.snap?.ops_rev !== undefined && (!st.ops || (st.ops.templates || []).length || (st.ops.runs || []).length);
    return h("nav", { class: "gchips", "aria-label": "Goals" }, ...list.map(chip),
      hasOps ? h("button", { class: `gchip${st.view === OPS_VIEW ? " is-on" : ""}`, type: "button", "data-goal": OPS_VIEW, "aria-pressed": String(st.view === OPS_VIEW), onclick: pickOps },
        h("span", { class: "gchip__name" }, "Operations")) : null,
      h("button", { class: "gchip gchip--new", type: "button", "data-act": "new-goal", onclick: () => goalSheet.open("") }, "+ New goal"));
  }

  // -- the goal's header: its flag, its title and numbers, the gate ------------------------------------------------------------------------------------
  function gateBox() {
    const g = st.gate;
    if (!g || g.same || !g.main) return null;                  // dev and main are one branch: there is no gate
    const n = (g.ideas || []).length, off = !g.commits && !n;
    const words = off ? "main is up to date" : `${n ? plural(n, "idea") : plural(g.commits, "commit")} in ${g.into} wait for ${g.main}`;
    return h("div", { class: "gate" },
      h("button", { class: "ork-btn primary gate__btn", type: "button", disabled: off, title: words, "aria-label": off ? `${g.into} → ${g.main}: ${words}` : `${g.into} → ${g.main}: ${words}. Open the gate`,
        "data-act": "gate", onclick: () => core.open({ kind: "gate" }, "gate") }, `${g.into} → ${g.main}`),
      h("span", { class: "cap" }, off ? "up to date" : `${n || g.commits} wait`));
  }

  function header(m) {
    const g = m.goal, v = g.verdict;
    const end = v ? (v.met ? `Met · ${v.by}` : `Not met yet · ${v.by}`) : m.left ? "The goal" : "Its ideas are done";
    const flag = h("span", { class: `trail-flag ${v ? (v.met ? "is-met" : "is-not") : ""}`.trim() }, icon("flag"));
    flags.raiseWhenSeen(g, flag);
    const mark = h("span", { class: "tport", role: "img", "aria-label": `The flag: ${end}`, title: end }, flag,
      h("span", { class: "ork-stat badge", title: "ideas left" }, String(m.left)));
    const today = g.today && g.today.merged ? `today ${g.today.merged} merged · ≈$${g.today.usd.toFixed(2)}` : "";
    return h("div", { class: "ghead" }, mark,
      h("button", { class: "ghead__body", type: "button", "aria-label": `Open goal ${g.title}`, title: g.title, onclick: () => core.open({ kind: "goal", slug: g.slug }, "map") },
        h("span", { class: "ghead__title" }, g.title),
        h("span", { class: "ghead__line" }, `${plural(m.left, "idea")} left · ${m.pct} % · ${money(g.usd)}`),
        today ? h("span", { class: "ghead__line" }, today) : null,
        v?.met && v.tally ? h("span", { class: "ghead__line trail-tally" }, tallyWords(v.tally)) : null),
      gateBox());
  }

  // -- the ideas bar: ▾ n · Now: …; open, the ideas at work and Done ----------------------------------------------------------------------------------------
  function ideasBar(m) {
    const open = st.ideasOpen;
    const head = h("button", { class: "ibar__head", type: "button", "aria-expanded": String(open), "data-act": "ideas", onclick: () => { st.ideasOpen = !open; core.draw(); } },
      h("i", { class: `ork-chev${open ? " up" : ""}`, "aria-hidden": "true" }), h("span", { class: "ork-count" }, String(m.ideas.length)),
      h("span", { class: "ibar__now" }, h("span", { class: "muted" }, "Now:"), ` ${m.now}`));
    const bar = h("div", { class: "ibar" }, head);
    if (!open) return bar;
    const row = (i) => h("button", { class: `irow${st.idea === i.slug ? " is-on" : ""}`, type: "button", "aria-pressed": String(st.idea === i.slug), "data-idea": i.slug, "aria-label": i.label,
      onclick: () => { st.idea = st.idea === i.slug ? "" : i.slug; st.ideasOpen = false; core.draw(); } },
    h("span", { class: "irow__top" }, h("span", { class: "irow__title" }, i.title), h("span", { class: "ork-pips", "aria-hidden": "true" }, ...i.pips.map((p) => h("i", { class: p })))),
    h("span", { class: "track", "aria-label": `Stage: ${i.stage}` }, ...i.track.flatMap((s, k) => [h("span", { class: s.state ? `is-${s.state}` : "" }, s.name), k < 2 ? h("i") : null])),
    h("span", { class: `irow__note${i.bad ? " no" : ""}` }, i.note));
    bar.append(h("div", { class: "ibar__list" }, h("h3", { class: "ork-label" }, "Ideas at work"), ...m.ideas.map(row),
      st.idea ? h("button", { class: "ork-btn quiet", type: "button", "data-act": "all-ideas", onclick: () => { st.idea = ""; st.ideasOpen = false; core.draw(); } }, "Show every idea’s tasks") : null,
      h("h3", { class: "ork-label" }, `Done · ${m.done.length}`),
      ...m.done.map((n) => h("button", { class: "done-row", type: "button", "data-idea": n.slug, onclick: () => { st.ideasOpen = false; core.open({ kind: "idea", slug: n.slug }, "map"); } },
        h("span", { class: "ok", "aria-hidden": "true" }, "✓"), h("span", { class: "done-row__t" }, ` ${n.short || n.title}`), h("span", { class: "cap" }, ` · ${doneWords(st.gate, n.slug)}`)))));
    return bar;
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

  const needsGoal = () => h("div", { class: "arena-empty" }, h("p", { class: "muted" }, "No goals yet."),
    h("button", { class: "ork-btn primary", type: "button", onclick: () => goalSheet.open("") }, "New goal"));

  return {
    el,
    sheets: [],
    /** Pick the goal of a stop (a push arrival, a link to Needs you) and show it. */
    show(slug) { if (slug) { st.track = slug; Object.assign(st, { view: "", band: "", focus: "", idea: "", ideasOpen: false }); core.draw(); } },
    /** The goal shown, from what the Board read and what this phone showed last. */
    goal: () => shownGoal(st, keptGoal(st.snap?.project)),
    draw() {
      const signature = JSON.stringify([st.map, st.board, st.agents, st.roles?.seats, st.roles?.library?.length, st.review, st.gate, st.today, st.track, st.view, st.band, st.focus, st.idea,
        st.ideasOpen, st.cards, st.ops, st.boardError, st.mapError, st.snap?.ops_rev, st.tick, Math.floor(Date.now() / 60000)]);
      if (!fresh(signature)) return;
      const card = cards.section(st.cards[0]);
      const lead = card ? [card] : [];
      if (!st.board && st.boardError) {                       // no project open: Operations is the person's, so it is offered all the same
        el.replaceChildren(...lead, chipRow([], ""), h("div", { class: "ops-view" }, h("p", { class: "muted" }, st.boardError), ...ops.section()));
        return;
      }
      if (!st.board || (!st.map && !st.mapError)) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, "Loading…")); return; }
      if (st.mapError && !st.map) { el.replaceChildren(...lead, h("p", { class: "muted arena-empty" }, st.mapError)); return; }
      const slug = shownGoal(st, keptGoal(st.snap?.project));
      if (slug && slug !== st.track) st.track = slug;
      const list = chipsOf(st);
      flags.seed(st.map.goals);
      const m = st.view === OPS_VIEW ? null : modelOf(st, slug);
      current = m;
      todayOf(slug, m);
      if (st.view === OPS_VIEW) { el.replaceChildren(...lead, chipRow(list, ""), opsView()); return; }
      if (!m) { el.replaceChildren(...lead, chipRow(list, ""), needsGoal()); return; }
      const band = st.band || m.first;
      const shown = band === "lead" ? [m.lead] : band === "build" ? m.build : m.check;
      if (st.focus && !shown.some((x) => x?.slug === st.focus)) st.focus = "";           // the member shown is not in this stage
      field.draw(m, { band, focus: st.focus, idea: st.idea }, stageSwitch(m, band));
      el.replaceChildren(...lead, chipRow(list, slug), header(m), ideasBar(m), field.el);
    },
  };
}
