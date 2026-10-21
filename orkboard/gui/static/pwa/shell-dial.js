// The create dial (docs/specs/49-one-window.md §10.2, §10.6; spec 50 §6.7): one button floating over the field's bottom right, 10 px above the bottom row (right 12 px), above everything
// there: a 48 px square in the action colour with the plus mark. The queues end there: the right column and a member's solo keep 64 px of room at their far end so that it covers no task. A tap
// opens the dial over a scrim: the button turns to × and three 48 px items stand above it, right-aligned: *New goal* (nearest the thumb, for the party shown: a blank card turns over from the
// button to the middle of the screen, ≈ 0.5 s in steps, and the full-screen New goal form opens; at once under reduced motion), *New party* (one of yours, or from the library: the New party
// sheet) and *Add to the party* (the party's seats, as Edit the party; its line counts the free seats). A tap on the scrim or × puts it away. It works with no signal (a goal is kept and sent
// when the town answers).
import { h, icon } from "./util.js";
import { modelOf, shownGoal } from "./shell-arena-words.js";
import { keptGoal } from "./shell-top.js";
import { motionOn } from "./shell-motion.js";

const TURN_MS = 500;                                 // the blank card from the button to the middle, turned over

/** *2 free seats in this party*, or *the party is full: change a member*. */
export function seatWords(free) {
  return free ? `${free} free ${free === 1 ? "seat" : "seats"} in this party` : "the party is full: change a member";
}

/** `core`: the board's frame (st, newIdea, editGoal, editParty). Returns {fab, sheets, show(on)}. */
export function makeDial(core) {
  const st = core.st;
  const fab = h("button", { class: "fab", type: "button", "aria-label": "Create: a new goal, a new party or a member of this one", "aria-haspopup": "menu", "aria-expanded": "false",
    hidden: true, "data-act": "create" }, icon("plus"));
  const menu = h("div", { class: "dial", role: "menu", "aria-label": "Create" });
  const dlg = h("dialog", { class: "dial-dlg", "aria-label": "Create" }, menu);
  const close = () => { if (dlg.close) dlg.close(); else dlg.removeAttribute("open"); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) close(); });                    // the scrim
  dlg.addEventListener("close", () => { fab.setAttribute("aria-expanded", "false"); });

  const item = (label, sub, run, { main = false, disabled = false } = {}) => h("button", { class: `dial__item${main ? " is-main" : ""}`, role: "menuitem", type: "button", disabled,
    "data-act": label.toLowerCase().replace(/\W+/g, "-"), onclick: () => { close(); run(); } }, h("b", {}, label), h("span", { class: "dial__sub" }, sub));

  /** A blank card turns over from the button to the middle of the screen, then `done` (the form opens). */
  function turn(from, done) {
    if (!motionOn() || !document.body.animate) { done(); return; }
    const card = h("span", { class: "drawcard" }, h("span", { class: "drawcard__back" }, icon("plus")), h("span", { class: "drawcard__face" }));
    const layer = h("div", { class: "drawlayer", "aria-hidden": "true" }, card);
    document.body.append(layer);
    const r = card.getBoundingClientRect();
    const dx = Math.round(from.left + from.width / 2 - (r.left + r.width / 2)), dy = Math.round(from.top + from.height / 2 - (r.top + r.height / 2));
    const run = card.animate([{ transform: `translate(${dx}px, ${dy}px) scale(0.3) rotateY(0deg)` }, { transform: "translate(0, 0) scale(1) rotateY(180deg)" }],
      { duration: TURN_MS, easing: "steps(8)", fill: "forwards" });
    run.finished.catch(() => {}).then(() => { layer.remove(); done(); });
  }

  fab.addEventListener("click", () => {
    const slug = shownGoal(st, keptGoal(st.snap?.project));
    const m = slug ? modelOf(st, slug) : null;
    const rect = fab.getBoundingClientRect();
    menu.style.right = `${Math.max(0, window.innerWidth - rect.right)}px`;                      // the × stands where the button stood
    menu.style.bottom = `${Math.max(0, window.innerHeight - rect.bottom)}px`;
    menu.replaceChildren(
      h("button", { class: "fab", type: "button", "aria-label": "Close", onclick: close }, icon("close")),
      h("button", { class: "dial__item is-main", role: "menuitem", type: "button", "data-act": "new-goal", onclick: () => { close(); turn(rect, () => core.newIdea()); } },
        h("b", {}, "New goal"), h("span", { class: "dial__sub" }, m ? `for ${m.goal.title}` : "its party first")),
      item("New party", "one of yours, or from the library", () => core.editGoal("")),
      item("Add to the party", m ? seatWords(m.freeBuild + m.freeCheck) : "a party comes first", () => core.editParty(slug), { disabled: !m }));
    fab.setAttribute("aria-expanded", "true");
    if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
  });

  return {
    fab,
    sheets: [dlg],
    /** The button is a party's (the Board read, not Operations'). */
    show(on) { fab.hidden = !on; },
  };
}
