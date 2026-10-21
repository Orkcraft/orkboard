// A spread (docs/specs/50-parties-and-goals.md §3.6, §6.6): a press on a stack of more lays its cards in a strip over the field — the line *<goal> · n tasks of <member> at this phase*, the cards
// (172 × 240) in a row that scrolls sideways and snaps to a card, each with its element, its phase, its mark, the goal's short name, its name, its dependency lines (no arrows on the phone) and its
// foot — over a dimmed field. A tap on a card opens it (the spread stays under that screen); *Put them back*, Esc or a tap on the dimmed field gathers them. Dealt from the stack's place to their own
// (≈ 0.3 s, 35 ms apart, in steps) and gathered the same way backwards; none under reduced motion. It holds its cards while it is open and closes itself when its stack is gone.
import { h } from "./util.js";
import { cardFace } from "./shell-decks.js";
import { motionOn } from "./shell-motion.js";

const DEAL_MS = 300;                                 // each card's trip
const STEP_MS = 35;                                  // one card after another
const plural = (n, one) => `${n} ${n === 1 ? one : `${one}s`}`;

/** `core`: the board's frame (open). Returns {node(), isOpen(), key(), open(info), close(animated), still(has)}; `info`: {key, member, ideaTitle, items, origin}. */
export function makeSpread(core) {
  let node = null, at = "";

  const trip = (card, from) => {                     // where a card travels from: the stack's place, to its own
    const r = card.getBoundingClientRect();
    return from ? `translate(${Math.round(from.left + from.width / 2 - (r.left + r.width / 2))}px, ${Math.round(from.top + from.height / 2 - (r.top + r.height / 2))}px) scale(0.6)` : "scale(0.6)";
  };
  const onKey = (e) => { if (e.key === "Escape" && node) { e.preventDefault(); close(); } };

  function close(animated = true) {
    if (!node) return;
    const gone = node;
    node = null;
    at = "";
    document.removeEventListener("keydown", onKey);
    const cards = [...gone.querySelectorAll(".spread__card")];
    if (!animated || !motionOn() || !gone.isConnected || !gone.__from) { gone.remove(); return; }
    gone.classList.add("is-gathering");               // the deal backwards: each card back to the stack, the last dealt first
    cards.forEach((c, i) => c.animate([{ transform: "none", opacity: 1 }, { transform: trip(c, gone.__from), opacity: 0.4 }],
      { duration: DEAL_MS, delay: (cards.length - 1 - i) * STEP_MS, easing: "steps(6)", fill: "forwards" }));
    setTimeout(() => gone.remove(), DEAL_MS + cards.length * STEP_MS + 20);
  }

  return {
    node: () => node,
    isOpen: () => Boolean(node),
    key: () => at,
    close,
    /** Lays the cards out; `host`: the field, which holds the spread over its columns. */
    open(info, host) {
      close(false);
      at = info.key;
      const n = info.items.length;
      const row = h("div", { class: "spread__row" }, ...info.items.map((it) => h("button", { class: "spread__card", type: "button", "data-key": it.key, title: it.tip, "aria-label": it.label,
        onclick: () => core.open(it.open, "map") }, cardFace(it, { spread: true }))));
      node = h("div", { class: "spread", role: "group", "aria-label": `${info.ideaTitle} · ${plural(n, "task")} of ${info.member} at this phase`, "data-key": info.key,
        onclick: (e) => { if (e.target === node) close(); } },
      h("p", { class: "spread__cap" }, h("b", {}, info.ideaTitle), ` · ${plural(n, "task")} of ${info.member} at this phase`), row,
      h("button", { class: "ork-btn", type: "button", "data-act": "put-back", onclick: () => close() }, "Put them back"));
      host.append(node);
      document.addEventListener("keydown", onKey);
      const from = info.origin?.getBoundingClientRect() || null;
      node.__from = from;
      if (motionOn()) [...row.children].forEach((c, i) => c.animate([{ transform: trip(c, from), opacity: 0.4 }, { transform: "none", opacity: 1 }],
        { duration: DEAL_MS, delay: i * STEP_MS, easing: "steps(6)", fill: "backwards" }));
      row.firstChild?.focus({ preventScroll: true });
    },
    /** The field was drawn again: a spread whose stack is gone (`has(key)` false) closes itself. */
    still(has) { if (node && !has(at)) close(false); },
  };
}
