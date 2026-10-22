// The create button (docs/specs/49-one-window.md §10.2; spec 50 §6.7; spec 52 §5.5): a small face-down deck floating over the field's bottom right, 10 px above the bottom row (right 12 px), above everything
// there — 48 × 64 px: two edges behind it and a back with the plus mark (orkUI's tokens: a hatched back, the action colour's edge). It does one thing: **New goal**. One tap and its top card lifts and the
// party's leader deals its goal types as a strip over the scrim (shell-types.js); a tap on one turns that card over and grows it from its place into the middle of the screen, ≈ 0.5 s in steps, and the
// full-screen New goal form opens by that type (the blank card: today's form). At once under reduced motion. A map with no `types` (an older host) turns the blank card as before. *New party* is in the
// parties' sheet (shell-where.js), *Add to the party* in About this party (shell-party.js). The queues end there: a column keeps 80 px of room at its far end so that the deck covers no task. It works
// with no signal (a goal is kept and sent when the town answers).
import { h, icon } from "./util.js";
import { sign } from "./shell-marks.js";
import { motionOn } from "./shell-motion.js";
import { makeTypes } from "./shell-types.js";

const TURN_MS = 500;                                 // the card from its place to the middle, lifted and turned over, in steps
const LIFT_PX = 14;                                  // how far the top card lifts before it turns
const LIFT_MS = 120;                                 // the deck's top card lifted before the types are dealt

/** `core`: the board's frame (st, newIdea). Returns {el, show(on)}. */
export function makeFab(core) {
  const st = core.st;
  const types = makeTypes(core);
  const back = h("span", { class: "deckfab__back" }, icon("plus"));
  const el = h("button", { class: "fab deckfab", type: "button", "aria-label": "New goal: pick its type, or a blank one", hidden: true, "data-act": "new-goal" },
    h("i", { class: "deckfab__edge e2", "aria-hidden": "true" }), h("i", { class: "deckfab__edge e1", "aria-hidden": "true" }), back);

  /** A card (a type's, with its sign; the blank one with the plus) lifts off its place, turns over and grows to the middle of the screen, then `done` (the form opens). */
  function turn(from, done, type = null) {
    if (!motionOn() || !el.animate) { done(); return; }
    const card = h("span", { class: "drawcard" }, h("span", { class: "drawcard__back" }, type ? sign(type.sign, "", { big: true }) : icon("plus")), h("span", { class: "drawcard__face" }));
    const layer = h("div", { class: "drawlayer", "aria-hidden": "true" }, card);
    document.body.append(layer);
    const r = card.getBoundingClientRect();
    const k = Math.max(0.32, Math.min(1, from.width / r.width));
    const dx = Math.round(from.left + from.width / 2 - (r.left + r.width / 2)), dy = Math.round(from.top + from.height / 2 - (r.top + r.height / 2));
    const run = card.animate([{ transform: `translate(${dx}px, ${dy}px) scale(${k}) rotateY(0deg)` },
      { transform: `translate(${dx}px, ${dy - LIFT_PX}px) scale(${k}) rotateY(0deg)`, offset: 0.2 },
      { transform: "translate(0, 0) scale(1) rotateY(180deg)" }], { duration: TURN_MS, easing: "steps(8)", fill: "forwards" });
    run.finished.catch(() => {}).then(() => { layer.remove(); done(); });
  }

  /** The deck's top card lifts, then `done` (none under reduced motion). */
  function lift(done) {
    if (!motionOn() || !back.animate) { done(); return; }
    back.animate([{ transform: "none" }, { transform: `translateY(-${LIFT_PX}px)` }, { transform: "none" }], { duration: LIFT_MS * 2, easing: "steps(4)" });
    setTimeout(done, LIFT_MS);
  }

  el.addEventListener("click", () => {
    const goal = (st.map?.goals || []).find((g) => g.slug === st.track);
    const from = el.getBoundingClientRect();
    if (!Array.isArray(goal?.types)) { turn(from, () => core.newIdea()); return; }        // an older host: the blank card, as before
    lift(() => types.open(goal, from, (type, rect) => turn(rect, () => core.newIdea(type), type)));
  });

  return {
    el,
    /** The button is a party's (the Board read, not Operations'). */
    show(on) { el.hidden = !on; if (!on) types.close(false); },
  };
}
