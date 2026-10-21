// The phone's top bar (docs/specs/33-v1-shell.md §6, spec 41 §2, spec 49 §10.1): the menu mark — it opens the drawer: Stop all, Spend today, Agents, the projects, the
// project's settings and the phone's (shell-projects.js, shell-drawer.js) · the project's name · Today (a clock and the count of the day's events: the Today sheet) ·
// what is left of the AI tools as one chip, the worst tool's diamonds (the tools sheet; shell-today.js). No frames: the words and icons alone. It slides away as the
// page scrolls down and comes back as it scrolls up. Roles only: warning at 20 % or less left, danger at 5 % or less. The goals are the chips under it (shell-arena.js).
import { h, icon } from "./util.js";
import { makeProjects } from "./shell-projects.js";
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
  const settings = makeSettings(core, ctx, { close: () => projects.sheet.close() }, () => tools.open());
  const projects = makeProjects(core, ctx, settings);
  const menu = h("button", { class: "bar-btn menu", type: "button", "aria-label": "Menu", "aria-haspopup": "dialog", onclick: () => projects.open() }, icon("menu"));
  const name = h("span", { class: "board-project" });
  const el = h("header", { class: "board-bar" }, menu, h("div", { class: "board-name" }, name), today.el, tools.el);

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
      projects.sync();
      if (window.scrollY <= el.offsetHeight) el.classList.remove("is-away");     // back at the top: always there
    },
    sheets: [...projects.sheets, tools.sheet.el, today.sheet.el],
    render(s, rev) {
      projects.render(s, rev);
      settings.render(s);
      tools.render(s);
      name.textContent = s.project || "";
      name.title = s.project || "";
    },
  };
}
