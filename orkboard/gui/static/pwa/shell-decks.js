// The cards of the field and the stacks they lie in (docs/specs/50-parties-and-goals.md §3.4, §6.5): a card (5:7) wears its goal's element top left, its mark top right (↻ at work, ✗ failed, the clock
// tonight, ! a stop: orkUI's signs), the goal's short name, the task's name and a foot (*working 12 min*, *failed*, *in Review*, *tonight*, *after k1, k2*); a stack is one goal's tasks of a member at
// one phase: the front card, behind it one or two edges, and *×n* on its corner. A press on a stack of one opens it; a stack of more spreads (shell-spread.js). Only nodes are made here.
import { h } from "./util.js";
import { elem, sign } from "./shell-marks.js";

const STATE = { running: "is-run", testing: "is-run", review: "is-review", ready: "is-next", waiting: "is-wait", held: "is-wait", failed: "is-fail", merged: "is-out", dropped: "is-out" };

/** A card's face: a span (the stack's button, or a card of a spread, is the thing pressed). `planning`: a goal of the leader's column (its words at the foot); `spread`: the phase word and the
 *  dependency lines are on it. */
export function cardFace(it, { planning = false, spread = false } = {}) {
  const cls = ["tcard"];
  if (planning) cls.push(it.kind === "stop" ? "is-stop" : it.kind === "busy" ? "is-run" : it.raw ? "is-raw" : "is-wait");
  else cls.push(STATE[it.state] || "");
  const dep = spread && !planning ? [it.dep?.before ? h("span", { class: "spread__dep" }, sign("before"), ` ${it.dep.before}`) : null,
    it.dep?.after ? h("span", { class: "spread__dep" }, sign("after"), ` ${it.dep.after}`) : null] : [];
  return h("span", { class: cls.filter(Boolean).join(" ") },
    h("span", { class: "tcard__top" }, elem(it.element, { dim: Boolean(it.raw) }), spread && !planning ? h("span", { class: "tcard__phase" }, it.phaseWord) : null,
      h("span", { class: "tcard__mark" }, it.sign ? sign(it.sign, it.signTip) : null)),
    h("span", { class: "tcard__idea" }, planning ? "Goal" : it.ideaTitle),
    h("span", { class: "tcard__name" }, it.title), ...dep, h("span", { class: "tcard__foot" }, it.words));
}

/** A stack as the field draws it: a button holding its edges, its front card and *×n*. `press(stack)` runs on a tap. `ghost`: a stack that left (`{sign}`: *check* a merge, *cross* a drop, none for a
 *  goal the filter put away), standing where it stood while it fades; `drawn`: it was not there a moment ago and rises. */
export function deckNode(stack, { press, planning = false, drawn = false, ghost = null, label = "" } = {}) {
  const top = stack.top, many = stack.n > 1;
  const edges = Math.min(stack.n - 1, 2);
  const kids = [...Array.from({ length: edges }, (_, i) => h("i", { class: `deck__edge e${edges - i}`, "aria-hidden": "true" })), cardFace(top, { planning }),
    many ? h("span", { class: "ork-gem deck__n", "aria-hidden": "true" }, `×${stack.n}`) : null];
  const cls = ["deck"];
  if (many) cls.push("is-many");
  if (planning) cls.push("is-goal");
  if (top.state === "failed" || (planning && top.kind === "stop")) cls.push(top.state === "failed" ? "is-fail" : "is-stop");
  if (drawn) cls.push("is-drawn");
  if (ghost) {
    return h("div", { class: `${cls.join(" ")} is-leaving`, "aria-hidden": "true", "data-ghost": stack.key, "data-sign": ghost.sign || "" }, ...kids,
      ghost.sign ? h("span", { class: "deck__flash" }, sign(ghost.sign, "", { big: true })) : null);
  }
  return h("button", { class: cls.join(" "), type: "button", title: top.tip, "aria-label": label || top.label, "data-key": stack.key, "data-idea": stack.idea, "data-phase": stack.phase || null,
    "data-n": String(stack.n), "data-task": !planning && !many ? top.id : null, "data-state": planning ? top.kind : top.state, onclick: () => press(stack) }, ...kids);
}
