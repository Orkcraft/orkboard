// The phone's top bar (docs/specs/33-v1-shell.md §6, spec 41 §2, spec 49 §10.1, spec 50 §6.1): the menu mark — it opens the drawer: Stop all, Spend today, Agents, the project's settings and the
// phone's, and Today (a clock, the word and the count of the day's events: the Today sheet; shell-drawer.js; the projects are not in it) · the *where* button (*harbor › Tech 4 ⌄*: the project, the party,
// the stops that wait; its sheet lists the parties and the other projects: shell-where.js) · what is left of the AI tools as one chip, the worst tool's diamonds alone (the tools sheet, the label and the title say the
// rest; shell-today.js). No frames: the words and icons alone. It slides away as the page scrolls down and comes back as it scrolls up. Roles only: warning at 20 % or less left, danger at 5 % or less.
import { h, icon, sheet } from "./util.js";
import { makeWhere, keepGoal, keptGoal } from "./shell-where.js";
import { foot } from "./shell-forms.js";
import { makeSettings } from "./shell-drawer.js";
import { makeToday, makeTools, resetWords } from "./shell-today.js";
import { WARN, DANGER, levelOf } from "./shell-limits.js";

export { WARN, DANGER, levelOf, resetWords, keepGoal, keptGoal };
const SLIDE_PX = 6;                       // a scroll this far down hides the bar, this far up brings it back

/** `core`: the board's frame (board.js). Returns {el, today, sheets, render(snapshot), draw()}. */
export function makeTop(core, ctx) {
  const tools = makeTools(core);
  const today = makeToday(core);
  const settings = makeSettings(core, ctx, { close: () => drawer.close() }, () => tools.open());
  const where = makeWhere(core, ctx);
  const drawer = sheet("Menu", ...settings.head, h("div", { class: "row" }, today.el), ...settings.project, ...settings.phone, foot(h("button", { class: "ork-btn primary big", type: "button", onclick: () => drawer.close() }, "Done")));
  drawer.el.classList.add("drawer");
  today.el.addEventListener("click", () => drawer.close());                      // Today's sheet opens over the menu, which is put away
  const menu = h("button", { class: "bar-btn menu", type: "button", "aria-label": "Menu: Stop all, Spend, Agents, Today and settings", "aria-haspopup": "dialog",
    onclick: () => { settings.sync(); drawer.open(); } }, icon("menu"));
  const el = h("header", { class: "board-bar" }, menu, where.el, h("span", { class: "spacer" }), tools.el);

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
      where.draw();                                                              // the party shown and what waits in it and in the others
      if (window.scrollY <= el.offsetHeight) el.classList.remove("is-away");     // back at the top: always there
    },
    sheets: [drawer.el, ...where.sheets, ...settings.sheets, tools.sheet.el, today.sheet.el],
    render(s, rev) {
      where.render(s, rev);
      settings.render(s);
      tools.render(s);
      where.draw();
    },
  };
}
