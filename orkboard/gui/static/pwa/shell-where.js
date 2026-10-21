// The top bar's *where* button and its sheet (docs/specs/50-parties-and-goals.md §6.1, decisions §63.12): beside the menu, one button that says where the phone is — *harbor › (the leader's head) Tech 4 ⌄*,
// the project's name muted, the party's short name in ink (600), the stops that wait in this party (warning) before the ⌄ and, after it, a small warning count of the stops that wait in the project's
// other parties, so that a question elsewhere is never hidden. 12 px text, a gap of 4 px, 44 px high, the party's name cut with an ellipsis when it must be. A tap opens one sheet from the top:
// the project's parties as rows (52 px at least: the leader's head, the name, *k/n done*, the stops' count, the work sign; the picked one marked; Operations too when the project has any),
// **+ New party**, then **Other projects** (shell-projects.js; a tap switches this phone to one). A pick is kept per project (`orkcraft.goal`) and puts the sheet away.
import { h, sheet, icon } from "./util.js";
import { sign } from "./shell-marks.js";
import { whoHead } from "./shell-who.js";
import { makeProjects } from "./shell-projects.js";
import { OPS_VIEW } from "./shell-ops.js";

const GOAL_KEPT = "orkcraft.goal";                    // {project: party slug}: the party this phone showed last
const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** The party this phone showed last in this project ("" none). */
export const keptGoal = (project) => { try { return (JSON.parse(localStorage.getItem(GOAL_KEPT)) || {})[project || ""] || ""; } catch { return ""; } };
export function keepGoal(project, slug) {
  try { localStorage.setItem(GOAL_KEPT, JSON.stringify({ ...(JSON.parse(localStorage.getItem(GOAL_KEPT)) || {}), [project || ""]: slug })); } catch { /* this run only */ }
}

/** `core`: the board's frame (st, parties(), pick(slug), pickOps(), editGoal(slug), call, close, reset, refresh); `ctx`: {send}. Returns {el, sheets, render(snapshot, rev), draw()}. */
export function makeWhere(core, ctx) {
  const st = core.st;
  const list = h("div", { class: "where-parties" });
  const others = makeProjects(core, ctx, () => sh.close());
  const sh = sheet("Parties", list, h("button", { class: "where-new", type: "button", "data-act": "new-party",
    onclick: () => { sh.close(); core.editGoal(""); } }, h("b", {}, "+ New party"), h("span", { class: "muted" }, "one of yours, or from the library")), others.el);
  sh.el.classList.add("top");

  const name = h("span", { class: "where__party" });
  const head = h("span", { class: "where__head" });
  const here = h("span", { class: "ork-count warning where__stops", hidden: true });
  const other = h("span", { class: "ork-count warning where__other", hidden: true });
  const project = h("span", { class: "where__project" });
  const btn = h("button", { class: "board-name where", type: "button", "aria-haspopup": "dialog", "data-act": "where", onclick: () => { draw(); sh.open(); others.load(); } },
    project, h("i", { class: "ork-chev right where__sep", "aria-hidden": "true" }), head, name, here, h("i", { class: "ork-chev", "aria-hidden": "true" }), other);

  const rowOf = (c, on) => h("button", { class: `where-row${on ? " is-on" : ""}`, type: "button", "aria-current": on ? "true" : null, "data-goal": c.slug,
    "aria-label": `${c.title}, ${c.done}${c.stops ? `, ${plural(c.stops, "stop waits", "stops wait")} for you` : ""}${c.working ? ", at work" : ""}`, onclick: () => { sh.close(); core.pick(c.slug); } },
  c.head ? whoHead(c.head, false) : h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, c.title), h("small", { class: "muted" }, c.done)),
  c.stops ? h("span", { class: "ork-count warning" }, String(c.stops)) : null, c.working ? sign("work", "at work") : null);

  function draw() {
    const p = core.parties();
    const opsOn = p.shown === OPS_VIEW;
    list.replaceChildren(...p.list.map((c) => rowOf(c, c.slug === p.shown)),
      p.ops ? h("button", { class: `where-row${opsOn ? " is-on" : ""}`, type: "button", "aria-current": opsOn ? "true" : null, "data-goal": OPS_VIEW,
        "aria-label": `Operations${p.ops.stops ? `, ${plural(p.ops.stops, "stop waits", "stops wait")} for you` : ""}`, onclick: () => { sh.close(); core.pickOps(); } },
      h("span", { class: "where-row__head" }), h("span", { class: "where-row__body" }, h("b", {}, "Operations")), p.ops.stops ? h("span", { class: "ork-count warning" }, String(p.ops.stops)) : null) : null);
    if (!p.list.length && !p.ops) list.replaceChildren(h("p", { class: "muted" }, "No parties yet."));
  }

  return {
    el: btn,
    sheets: [sh.el],
    render(s, rev) {
      others.render(s, rev);
      project.textContent = s.project || "";
    },
    /** The button drawn again with the Board (and an open sheet with it). */
    draw() {
      const p = core.parties();
      const c = p.list.find((x) => x.slug === p.shown);
      const label = p.shown === OPS_VIEW ? "Operations" : c?.short || "";
      name.textContent = label;
      head.replaceChildren(...[c?.head && p.shown !== OPS_VIEW ? whoHead(c.head, false) : null].filter(Boolean));
      btn.classList.toggle("is-bare", !label);
      btn.dataset.goal = p.shown;                                                // the party shown (a test's and a reader's hold)
      here.hidden = !p.here;
      here.textContent = String(p.here || "");
      other.hidden = !p.other;
      other.textContent = String(p.other || "");
      const project_ = st.snap?.project || "";
      const said = [project_ ? `Project ${project_}` : "", label ? `party ${label}` : "", p.here ? `${plural(p.here, "stop waits", "stops wait")} for you here` : "",
        p.other ? `${plural(p.other, "stop waits", "stops wait")} for you in the other parties` : ""].filter(Boolean).join(", ");
      btn.setAttribute("aria-label", `${said || "Project"}. A tap shows the parties and the other projects`);
      btn.title = [project_, label].filter(Boolean).join(" › ");
      if (sh.el.open) draw();
    },
  };
}
