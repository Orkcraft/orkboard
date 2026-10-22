// The create button (docs/specs/49-one-window.md §10.2; spec 50 §6.7; spec 53 §2.1): a small face-down deck floating over the field's bottom right, 10 px above the bottom row (right 12 px), above everything
// there — 48 × 64 px: two edges behind it and a back with the plus mark (orkUI's tokens: a hatched back, the action colour's edge). It does one thing: **New goal**. One tap and the form slides up
// at once (shell-ideas.js; no lift, no deal, no turn: spec 53 drops spec 52 §5.5's); the party and the goal type are picked in the form. *New party* is in the parties' sheet (shell-where.js) and in the
// form's party list, *Add to the party* in About this party (shell-party.js). The queues end there: a column keeps 80 px of room at its far end so that the deck covers no task. It works
// with no signal (a goal is kept and sent when the town answers).
import { h, icon } from "./util.js";

/** `core`: the board's frame (newIdea). Returns {el, show(on)}. */
export function makeFab(core) {
  const back = h("span", { class: "deckfab__back" }, icon("plus"));
  const el = h("button", { class: "fab deckfab", type: "button", "aria-label": "New goal", hidden: true, "data-act": "new-goal" },
    h("i", { class: "deckfab__edge e2", "aria-hidden": "true" }), h("i", { class: "deckfab__edge e1", "aria-hidden": "true" }), back);
  el.addEventListener("click", () => core.newIdea());

  return {
    el,
    /** The button is a party's (the Board read, not Operations'). */
    show(on) { el.hidden = !on; },
  };
}
