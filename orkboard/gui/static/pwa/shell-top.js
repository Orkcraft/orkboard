// The phone's top bar (docs/specs/33-v1-shell.md §6, spec 41 §2, spec 49 §10.1, spec 50 §6.1): the menu mark — it opens the drawer: Stop all, Spend today, Agents, the project's settings and the
// phone's (shell-drawer.js; the projects are not in it) · the project's name, a button (*harbor ⌄*) that opens the Projects sheet from the top (shell-projects.js) · Today (a clock and the count of the day's events: the Today sheet) ·
// what is left of the AI tools as one chip, the worst tool's diamonds (the tools sheet; shell-today.js). No frames: the words and icons alone. It slides away as the
// page scrolls down and comes back as it scrolls up. Roles only: warning at 20 % or less left, danger at 5 % or less. The goals are the chips under it (shell-arena.js).
import { h, icon, sheet } from "./util.js";
import { makeProjects } from "./shell-projects.js";
import { foot } from "./shell-forms.js";
import { makeSettings } from "./shell-drawer.js";
import { makeToday, makeTools, resetWords } from "./shell-today.js";
import { WARN, DANGER, levelOf } from "./shell-limits.js";

export { WARN, DANGER, levelOf, resetWords };
const GOAL_KEPT = "orkcraft.goal";                    // {project: goal slug}: the goal this phone showed last
const SLIDE_PX = 6;                       // a scroll this far down hides the bar, this far up brings it back

/** The goal this phone showed last in this project ("" none). */
export const keptGoal = (project) => { try { return (JSON.parse(localStorage.getItem(GOAL_KEPT)) || {})[project || ""] || ""; } catch { return ""; } };
export function keepGoal(project, slug) {
  try { localStorage.setItem(GOAL_KEPT, JSON.stringify({ ...(JSON.parse(localStorage.getItem(GOAL_KEPT)) || {}), [project || ""]: slug })); } catch { /* this run only */ }
}

/** `core`: the board's frame (board.js). Returns {el, today, sheets, render(snapshot), draw()}. */
export function makeTop(core, ctx) {
  const tools = makeTools(core);
  const today = makeToday(core);
  const settings = makeSettings(core, ctx, { close: () => drawer.close() }, () => tools.open());
  const projects = makeProjects(core, ctx);
  const drawer = sheet("Menu", ...settings.head, ...settings.project, ...settings.phone, foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => drawer.close() }, "Done")));
  drawer.el.classList.add("drawer");
  const menu = h("button", { class: "bar-btn menu", type: "button", "aria-label": "Menu: Stop all, Spend, Agents and settings", "aria-haspopup": "dialog",
    onclick: () => { settings.sync(); drawer.open(); } }, icon("menu"));
  const name = h("span", { class: "board-project" });
  const pick = h("button", { class: "board-name", type: "button", "aria-haspopup": "dialog", onclick: () => projects.open() }, name, h("i", { class: "ork-chev", "aria-hidden": "true" }));
  const el = h("header", { class: "board-bar" }, menu, pick, h("span", { class: "spacer" }), today.el, tools.el);

  // Slides away as the page scrolls down, back as it scrolls up (or near the top); never while a screen is open over the board.
  let lastY = window.scrollY;
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    if (Math.abs(y - lastY) < SLIDE_PX) return;
    el.classList.toggle("is-away", y > lastY && y > el.offsetHeight);
    lastY = y;
  }, { passive: true });

  return {
    el,
    today,
    /** The bar drawn again with the Board. */
    draw() {
      if (drawer.el.open) settings.sync();                                       // an open menu shows what the Board read
      if (window.scrollY <= el.offsetHeight) el.classList.remove("is-away");     // back at the top: always there
    },
    sheets: [drawer.el, ...projects.sheets, ...settings.sheets, tools.sheet.el, today.sheet.el],
    render(s, rev) {
      projects.render(s, rev);
      settings.render(s);
      tools.render(s);
      name.textContent = s.project || "";
      pick.title = s.project || "";
      pick.setAttribute("aria-label", `Project: ${s.project || "none"}. A tap shows the others`);
    },
  };
}
