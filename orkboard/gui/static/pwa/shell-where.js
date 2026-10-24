// The project's button and the parties' sheet (docs/specs/52-goal-types.md §5.1, §5.3; decisions §65.3, which reverses §63.12's party half): beside the menu, the project's button — *harbor ⌄*, the
// project's name (12 px, 44 px high) — whose sheet from the top is **Projects**: *this one* (the project shown, marked), the other projects with what waits in each, a tap switching this phone to one
// (shell-projects.js). The party is not in the top bar: it is the **deck** at the goals bar's left (spec 53 §1.1: a 44 × 44 target round a back of 16 × 22 with two edges behind it and the chevron down; no count: spec 54 §2.4, decisions §67.3 —
// what waits lies in the hand, and the sheet says where by a dot). A tap on the deck opens the parties' sheet from the top: the parties as rows (52 px at least: the leader's head, the name,
// *k/n done*, a dot where a stop waits (8 × 8, danger when one of them failed, else alert), the work sign; the one shown marked), Operations' row when the project has any, **+ New party**. A pick is kept per project (`orkcraft.goal`) and puts the sheet away.
// A party just saved on New party gathers its heads into the deck, in the first draw that shows it (spec 63 §4: shell-motion.js `gather`).
import { h, head, sheet } from "./util.js";
import { sign } from "./shell-marks.js";
import { whoHead } from "./shell-who.js";
import { makeProjects } from "./shell-projects.js";
import { OPS_VIEW } from "./shell-ops.js";
import { gather, gatherTo, motionOn } from "./shell-motion.js";
import { PROJECT, makeProject, projectOf } from "./shell-project.js";

const GOAL_KEPT = "orkcraft.goal";                    // {project: party slug}: the party this phone showed last
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The party's deck's label (spec 52 §5.3): *Parties: Tech shown, 2 stops wait in the other parties. A tap shows the parties*; `p`: shell-arena-words.js `partiesOf`. The count is for a screen reader only: nothing on the screen counts the stops. */
export function deckWords(p) {
  const shown = p.shown === OPS_VIEW ? "Operations" : p.list.find((c) => c.slug === p.shown)?.short || "";
  return `Parties: ${shown ? `${shown} shown` : "none yet"}${p.other ? `, ${plural(p.other, "stop waits", "stops wait")} in the other parties` : ""}. A tap shows the parties`;
}

/** The party this phone showed last in this project ("" none). */
export const keptGoal = (project) => { try { return (JSON.parse(localStorage.getItem(GOAL_KEPT)) || {})[project || ""] || ""; } catch { return ""; } };
export function keepGoal(project, slug) {
  try { localStorage.setItem(GOAL_KEPT, JSON.stringify({ ...(JSON.parse(localStorage.getItem(GOAL_KEPT)) || {}), [project || ""]: slug })); } catch { /* this run only */ }
}

/** `core`: the board's frame (st, parties(), pick(slug), pickOps(), editGoal(slug), call, close, reset, refresh); `ctx`: {send}.
 *  Returns {el, sheets, render(snapshot, rev), draw(), deck(), openParties()}: `el` is the project's button, `deck()` a new party's deck for the stage switch. */
export function makeWhere(core, ctx) {
  const st = core.st;
  const projects = makeProjects(core, ctx, () => mine.close());
  const mine = sheet("Projects", projects.el);
  mine.el.classList.add("top");
  const list = h("div", { class: "where-parties" });
  // The project's level (spec 70 §2.1, §2.4): the Orkmaster's row at the parties' sheet's top opens its sheet; *Open <party>* there switches the board and says `ideas.shown {party, from: "@project"}`.
  const level = makeProject(core, { openParty(slug) { shown(slug, PROJECT); core.pick(slug); } });
  const sh = sheet("Parties", list, h("button", { class: "where-new", type: "button", "data-act": "new-party",
    onclick: () => { sh.close(); core.editGoal(""); } }, h("b", {}, "+ New party"), h("span", { class: "muted" }, "one of yours, or from the library")));
  sh.el.classList.add("top");

  const name = h("span", { class: "projbtn__name" });
  const btn = h("button", { class: "board-name projbtn", type: "button", "aria-haspopup": "dialog", "data-act": "project", onclick: () => { mine.open(); projects.load(); } },
    name, h("i", { class: "ork-chev", "aria-hidden": "true" }));

  /** A switch to another party is said to the host (`ideas.shown {party, from}`, spec 68 §4, §7.9), fire and forget: never waited for, never a toast; not said for the party already shown, nor on a redraw. */
  function shown(to, from = "") {
    const now = core.parties().shown;
    if (!to || (!from && to === now)) return;
    const was = from || (now && now !== OPS_VIEW ? now : "");
    try { Promise.resolve(ctx.send("ideas.shown", { party: to, ...(was ? { from: was } : {}) })).catch(() => {}); } catch { /* it is only counted */ }
  }

  /** A stop's dot, where a count was: 8 × 8, danger when one of the stops failed, else alert. */
  const dot = (stops, failed) => (stops ? h("span", { class: `where-dot ${failed ? "danger" : "alert"}`, "aria-hidden": "true", "data-dot": failed ? "danger" : "alert" }) : null);
  const rowOf = (c, on) => h("button", { class: `where-row${on ? " is-on" : ""}`, type: "button", "aria-current": on ? "true" : null, "data-goal": c.slug,
    "aria-label": `${c.title}, ${c.done}${c.stops ? `${c.failed ? ", a stop failed" : ""}, something waits for you` : ""}${c.working ? ", at work" : ""}`, onclick: () => { sh.close(); shown(c.slug); core.pick(c.slug); } },
  c.head ? whoHead(c.head, false) : h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, c.title), h("small", { class: "muted" }, c.done)),
  dot(c.stops, c.failed), c.working ? sign("work", "at work") : null);

  /** *The project* at the sheet's top: the Orkmaster's head, its name and what it shows; none for a host that sends no `project`. */
  function projectRow() {
    const o = projectOf(core)?.orkmaster;
    if (!o) return null;
    return h("button", { class: "where-row where-project", type: "button", "data-act": "the-project", "aria-haspopup": "dialog", onclick: () => { sh.close(); shown(PROJECT); level.open(); } },
      head(o.race, o.tier, { title: "Orkmaster" }), h("span", { class: "where-row__body" }, h("b", {}, "The project"), h("small", { class: "muted" }, "The parties, their goals")), h("i", { class: "ork-chev right", "aria-hidden": "true" }));
  }

  function drawList() {
    const p = core.parties();
    const opsOn = p.shown === OPS_VIEW;
    list.replaceChildren(...[projectRow(), ...p.list.map((c) => rowOf(c, c.slug === p.shown)),
      p.ops ? h("button", { class: `where-row${opsOn ? " is-on" : ""}`, type: "button", "aria-current": opsOn ? "true" : null, "data-goal": OPS_VIEW,
        "aria-label": `Operations${p.ops.stops ? `${p.ops.failed ? ", a stop failed" : ""}, something waits for you` : ""}`, onclick: () => { sh.close(); core.pickOps(); } },
      h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, "Operations")), dot(p.ops.stops, p.ops.failed)) : null].filter(Boolean));
    if (!p.list.length && !p.ops) list.replaceChildren(...[projectRow(), h("p", { class: "muted" }, "No parties yet.")].filter(Boolean));
  }
  function openParties() { drawList(); sh.open(); }

  return {
    el: btn,
    sheets: [mine.el, sh.el, level.el],
    openParties,
    /** The party's deck at the goals bar's left: 44 × 44, with no count (the stops lie in the hand; the label tells a screen reader how many wait in the other parties). */
    deck() {
      const p = core.parties();
      const node = h("button", { class: "partydeck", type: "button", "aria-haspopup": "dialog", "data-act": "parties", "data-goal": p.shown, "aria-label": deckWords(p), onclick: openParties },
        h("i", { class: "partydeck__edge e2", "aria-hidden": "true" }), h("i", { class: "partydeck__edge e1", "aria-hidden": "true" }),
        h("span", { class: "partydeck__back", "aria-hidden": "true" }, h("i", { class: "ork-chev" })));
      const waiting = gather.live();
      if (waiting && waiting.party === p.shown) {         // the first draw that shows the party New party saved: its heads gather into this deck once it is in the page (spec 63 §4.2)
        gather.drop();
        if (motionOn()) requestAnimationFrame(() => gatherTo(waiting));
      }
      return node;
    },
    render(s, rev) {
      projects.render(s, rev);
      name.textContent = s.project || "";
    },
    /** The button drawn again with the Board (and an open parties' sheet with it). */
    draw() {
      const project = st.snap?.project || "";
      btn.setAttribute("aria-label", `Project${project ? ` ${project}` : ""}. A tap shows your projects`);
      btn.title = project;
      if (sh.el.open) drawList();
      level.draw();
    },
  };
}
