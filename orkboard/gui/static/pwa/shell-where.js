// The project's button and the parties' sheet (docs/specs/52-goal-types.md §5.1, §5.3; decisions §65.3, which reverses §63.12's party half): beside the menu, the project's button — *harbor ⌄*, the
// project's name (12 px, 44 px high) — whose sheet from the top is **Projects**: *this one* (the project shown, marked), the other projects with what waits in each, a tap switching this phone to one
// (shell-projects.js). The party is not in the top bar: it is the stage switch's **deck** at its end (a small deck, two edges behind a back with the chevron down, the warning count of the stops that
// wait in the project's other parties and in Operations at its top right). A tap on the deck opens the parties' sheet from the top: the parties as rows (52 px at least: the leader's head, the name,
// *k/n done*, the stops' count, the work sign; the one shown marked), Operations' row when the project has any, **+ New party**. A pick is kept per project (`orkcraft.goal`) and puts the sheet away.
import { h, sheet } from "./util.js";
import { sign } from "./shell-marks.js";
import { whoHead } from "./shell-who.js";
import { makeProjects } from "./shell-projects.js";
import { OPS_VIEW } from "./shell-ops.js";

const GOAL_KEPT = "orkcraft.goal";                    // {project: party slug}: the party this phone showed last
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The party's deck's label (spec 52 §5.3): *Parties: Tech shown, 2 stops wait in the other parties. A tap shows the parties*; `p`: shell-arena-words.js `partiesOf`. */
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
  const sh = sheet("Parties", list, h("button", { class: "where-new", type: "button", "data-act": "new-party",
    onclick: () => { sh.close(); core.editGoal(""); } }, h("b", {}, "+ New party"), h("span", { class: "muted" }, "one of yours, or from the library")));
  sh.el.classList.add("top");

  const name = h("span", { class: "projbtn__name" });
  const btn = h("button", { class: "board-name projbtn", type: "button", "aria-haspopup": "dialog", "data-act": "project", onclick: () => { mine.open(); projects.load(); } },
    name, h("i", { class: "ork-chev", "aria-hidden": "true" }));

  const rowOf = (c, on) => h("button", { class: `where-row${on ? " is-on" : ""}`, type: "button", "aria-current": on ? "true" : null, "data-goal": c.slug,
    "aria-label": `${c.title}, ${c.done}${c.stops ? `, ${plural(c.stops, "stop waits", "stops wait")} for you` : ""}${c.working ? ", at work" : ""}`, onclick: () => { sh.close(); core.pick(c.slug); } },
  c.head ? whoHead(c.head, false) : h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, c.title), h("small", { class: "muted" }, c.done)),
  c.stops ? h("span", { class: "ork-count warning" }, String(c.stops)) : null, c.working ? sign("work", "at work") : null);

  function drawList() {
    const p = core.parties();
    const opsOn = p.shown === OPS_VIEW;
    list.replaceChildren(...p.list.map((c) => rowOf(c, c.slug === p.shown)),
      p.ops ? h("button", { class: `where-row${opsOn ? " is-on" : ""}`, type: "button", "aria-current": opsOn ? "true" : null, "data-goal": OPS_VIEW,
        "aria-label": `Operations${p.ops.stops ? `, ${plural(p.ops.stops, "stop waits", "stops wait")} for you` : ""}`, onclick: () => { sh.close(); core.pickOps(); } },
      h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, "Operations")), p.ops.stops ? h("span", { class: "ork-count warning" }, String(p.ops.stops)) : null) : null);
    if (!p.list.length && !p.ops) list.replaceChildren(h("p", { class: "muted" }, "No parties yet."));
  }
  function openParties() { drawList(); sh.open(); }

  return {
    el: btn,
    sheets: [mine.el, sh.el],
    openParties,
    /** The party's deck at the end of the stage switch: 52 × 52, the count of the stops that wait in the other parties (none when none: the one count of stops on the screen). */
    deck() {
      const p = core.parties();
      return h("button", { class: "partydeck", type: "button", "aria-haspopup": "dialog", "data-act": "parties", "data-goal": p.shown, "aria-label": deckWords(p), onclick: openParties },
        h("i", { class: "partydeck__edge e2", "aria-hidden": "true" }), h("i", { class: "partydeck__edge e1", "aria-hidden": "true" }),
        h("span", { class: "partydeck__back", "aria-hidden": "true" }, h("i", { class: "ork-chev" })),
        p.other ? h("span", { class: "ork-count warning partydeck__n", "aria-hidden": "true" }, String(p.other)) : null);
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
    },
  };
}
