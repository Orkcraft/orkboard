// The create dial (docs/specs/49-one-window.md §10.2, §10.6): one button floating over the field's bottom right, 10 px above the bottom row (right 12 px), above everything
// there: a 48 px square in the action colour with the plus mark — New idea, as the phone has had it (spec 41 §5), and now the way to the others. The queues end there: the right
// column and a member's solo keep 64 px of room at their far end so that it covers no task. A tap opens the dial over a scrim: the button turns to × and three 48 px items stand
// above it, right-aligned: *New idea* (nearest the thumb, for the goal shown: today's New idea sheet), *New goal* (today's New goal sheet) and *Add to the party* (the goal's
// party, as Edit the party; its line counts the free seats). A tap on the scrim or × puts it away. It works with no signal (New idea
// is kept and sent when the town answers).
import { h, icon } from "./util.js";
import { modelOf, shownGoal } from "./shell-arena-words.js";
import { keptGoal } from "./shell-top.js";

/** *2 free seats in this party*, or *the party is full: change a member*. */
export function seatWords(free) {
  return free ? `${free} free ${free === 1 ? "seat" : "seats"} in this party` : "the party is full: change a member";
}

/** `core`: the board's frame (st, newIdea, editGoal, editParty). Returns {fab, sheets, show(on)}. */
export function makeDial(core) {
  const st = core.st;
  const fab = h("button", { class: "fab", type: "button", "aria-label": "Create: a new idea, a new goal or a member of the party", "aria-haspopup": "menu", "aria-expanded": "false",
    hidden: true, "data-act": "create" }, icon("plus"));
  const menu = h("div", { class: "dial", role: "menu", "aria-label": "Create" });
  const dlg = h("dialog", { class: "dial-dlg", "aria-label": "Create" }, menu);
  const close = () => { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) close(); });                    // the scrim
  dlg.addEventListener("close", () => { fab.setAttribute("aria-expanded", "false"); });

  const item = (label, sub, run, { main = false, disabled = false } = {}) => h("button", { class: `dial__item${main ? " is-main" : ""}`, role: "menuitem", type: "button", disabled,
    "data-act": label.toLowerCase().replace(/\W+/g, "-"), onclick: () => { close(); run(); } }, h("b", {}, label), h("span", { class: "dial__sub" }, sub));

  fab.addEventListener("click", () => {
    const slug = shownGoal(st, keptGoal(st.snap?.project));
    const m = slug ? modelOf(st, slug) : null;
    const rect = fab.getBoundingClientRect();
    menu.style.right = `${Math.max(0, window.innerWidth - rect.right)}px`;                      // the × stands where the button stood
    menu.style.bottom = `${Math.max(0, window.innerHeight - rect.bottom)}px`;
    menu.replaceChildren(
      h("button", { class: "fab", type: "button", "aria-label": "Close", onclick: close }, icon("close")),
      item("New idea", m ? `for ${m.goal.title}` : "its goal first", () => core.newIdea(), { main: true }),
      item("New goal", "its title, what done means, its party", () => core.editGoal("")),
      item("Add to the party", m ? seatWords(m.freeBuild + m.freeCheck) : "a goal comes first", () => core.editParty(slug), { disabled: !m }));
    fab.setAttribute("aria-expanded", "true");
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  });

  return {
    fab,
    sheets: [dlg],
    /** The button is a goal's (the Board read, not Operations'). */
    show(on) { fab.hidden = !on; },
  };
}
