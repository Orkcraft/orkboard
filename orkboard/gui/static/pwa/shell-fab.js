// The create button (docs/specs/49-one-window.md §10.2; spec 50 §6.7): a small face-down deck floating over the field's bottom right, 10 px above the bottom row (right 12 px), above everything there —
// 48 × 64 px: two edges behind it and a back with the plus mark (orkUI's tokens: a hatched back, the action colour's edge). It does one thing: **New goal**. One tap and its top card lifts, turns over and
// grows into the middle of the screen, ≈ 0.5 s in steps, and the full-screen New goal form opens (at once under reduced motion). *New party* is in the *where* sheet (shell-where.js), *Add to the
// party* in About this party (shell-party.js). The queues end there: a column keeps 80 px of room at its far end so that the deck covers no task. It works with no signal (a goal is kept and sent when
// the town answers).
import { h, icon } from "./util.js";
import { motionOn } from "./shell-motion.js";

const TURN_MS = 500;                                 // the card from the deck to the middle, lifted and turned over, in steps
const LIFT_PX = 14;                                  // how far the top card lifts before it turns

/** `core`: the board's frame (newIdea). Returns {el, show(on)}. */
export function makeFab(core) {
  const el = h("button", { class: "fab deckfab", type: "button", "aria-label": "New goal: draw a blank one", hidden: true, "data-act": "new-goal" },
    h("i", { class: "deckfab__edge e2", "aria-hidden": "true" }), h("i", { class: "deckfab__edge e1", "aria-hidden": "true" }), h("span", { class: "deckfab__back" }, icon("plus")));

  /** The top card (a blank card) lifts off the deck, turns over and grows to the middle of the screen, then `done` (the form opens). */
  function turn(from, done) {
    if (!motionOn() || !el.animate) { done(); return; }
    const card = h("span", { class: "drawcard" }, h("span", { class: "drawcard__back" }, icon("plus")), h("span", { class: "drawcard__face" }));
    const layer = h("div", { class: "drawlayer", "aria-hidden": "true" }, card);
    document.body.append(layer);
    const r = card.getBoundingClientRect();
    const dx = Math.round(from.left + from.width / 2 - (r.left + r.width / 2)), dy = Math.round(from.top + from.height / 2 - (r.top + r.height / 2));
    const run = card.animate([{ transform: `translate(${dx}px, ${dy}px) scale(0.32) rotateY(0deg)` },
      { transform: `translate(${dx}px, ${dy - LIFT_PX}px) scale(0.32) rotateY(0deg)`, offset: 0.2 },
      { transform: "translate(0, 0) scale(1) rotateY(180deg)" }], { duration: TURN_MS, easing: "steps(8)", fill: "forwards" });
    run.finished.catch(() => {}).then(() => { layer.remove(); done(); });
  }

  el.addEventListener("click", () => turn(el.getBoundingClientRect(), () => core.newIdea()));

  return {
    el,
    /** The button is a party's (the Board read, not Operations'). */
    show(on) { el.hidden = !on; },
  };
}
