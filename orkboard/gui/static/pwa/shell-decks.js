// The cards of the field and the stacks they lie in (docs/specs/50-parties-and-goals.md §3.4, §6.5; spec 67 §2): a token of the field (74 px, 5:7) wears its goal's element top left and its goal's type's sign top right, in the element's colour (none for a goal with no type; spec 55), its name and one value at its foot (the time at work, the hour of a hold; `it.value`); a card of a spread keeps the goal's line and its state in words (*working 12 min*, *failed*, *in Review*, *tonight*, *after Challenge store*); a stack is one goal's tasks of a member at
// one phase: the front card, behind it one or two edges, and *×n* on its corner. A press on a stack of one opens it; a stack of more spreads (shell-spread.js). Only nodes are made here.
import { h } from "./util.js";
import { elem, sign, typeTone } from "./shell-marks.js";

const STATE = { running: "is-run", testing: "is-run", review: "is-review", picking: "is-stop", ready: "is-next", waiting: "is-wait", held: "is-wait", failed: "is-fail", merged: "is-out", dropped: "is-out" };

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
      it.type ? h("span", { class: `tcard__type ${typeTone(it.element, it.raw)}`, "data-type": it.type.id }, sign(it.type.sign, it.type.name)) : null),
    spread ? h("span", { class: "tcard__idea" }, planning ? (it.type ? it.type.name : "Goal") : it.ideaTitle) : null,        // the field's token has no goal's line (spec 67 §2.2)
    h("span", { class: "tcard__name" }, it.title), ...dep, spread ? h("span", { class: "tcard__foot" }, it.words) : it.value ? h("span", { class: "tcard__foot" }, it.value) : null);
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
  if (top.state === "failed" || top.state === "picking" || (planning && top.kind === "stop")) cls.push(top.state === "failed" ? "is-fail" : "is-stop");
  if (drawn) cls.push("is-drawn");
  if (ghost) {
    return h("div", { class: `${cls.join(" ")} is-leaving`, "aria-hidden": "true", "data-ghost": stack.key, "data-sign": ghost.sign || "" }, ...kids,
      ghost.sign ? h("span", { class: "deck__flash" }, sign(ghost.sign, "", { big: true })) : null);
  }
  return h("button", { class: cls.join(" "), type: "button", title: top.tip, "aria-label": label || top.label, "data-key": stack.key, "data-idea": stack.idea, "data-phase": stack.phase || null,
    "data-n": String(stack.n), "data-task": !planning && !many ? top.id : null, "data-state": planning ? top.kind : top.state, onclick: () => press(stack) }, ...kids);
}
