// A spread (docs/specs/50-parties-and-goals.md §3.6, §4.1): a press on a stack of more than one card dims the field and deals its cards in a row
// over it (120 × 168, centred, wrapped when they do not fit), each from the stack's place to its own (≈ 0.3 s, 35 ms apart, in steps), over the line
// *<goal> · n tasks of <member> at this phase*. Each card has the goal's element, its phase word, its mark, the goal's short name, the task's name, its
// dependency lines (*waits for …*, *n wait for it*) and its foot; a press on one opens it (the spread stays under the drawer). *Put them back*, Esc or a
// press on the scrim gathers them (the deal backwards). No deal under reduced motion. A spread holds the cards it was dealt; it closes itself
// when its stack is gone. Under the party row: the members' numbers keep updating over it. The parties' spread (goaltabs.js) and the goal types'
// (types.js, spec 52 §3.4, §4.1) are dealt the same way (`dealCards`).
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { reducedMotion } from "./motion.js";
import { spread, taskHover, taskHoverBy } from "./arenastate.js";
import { columnOf, depLines, plural, taskFoot } from "./arenawords.js";
import { CardBody, cardTip, footParts, keyOf, open, relationOf, stateCls } from "./stacks.js";

const DEAL_MS = 300, APART_MS = 35;
let gather = null;                                  // the open spread's way out (its cards go back first)

/** Gathers the open spread: its cards go back to the stack, then it is gone. With none open, nothing. */
export function closeSpread() {
  if (gather) gather();
  else spread.value = null;
}

/** Deals the cards (`.arena-spread__card` under `root`) from `from` (the stack's or the deck's place, a rect) to their own places (`to`: true), or back
 *  to it, then `done`. At once under reduced motion, while the page is hidden, or with no place to deal from. */
export function dealCards(root, from, to, done) {
  const list = root ? [...root.querySelectorAll(".arena-spread__card")] : [];
  if (!root || !from || reducedMotion() || document.hidden || !list.length || typeof list[0].animate !== "function") { done(); return; }
  const fx = from.left + from.width / 2, fy = from.top + from.height / 2;
  list.forEach((card, i) => {
    const r = card.getBoundingClientRect(), dx = fx - (r.left + r.width / 2), dy = fy - (r.top + r.height / 2);
    const keys = [{ transform: `translate(${dx}px, ${dy}px) scale(0.86)`, opacity: 0.2 }, { transform: "none", opacity: 1 }];
    card.animate(to ? keys : [...keys].reverse(), { duration: DEAL_MS, delay: (to ? i : list.length - 1 - i) * APART_MS, easing: "steps(6)", fill: to ? "backwards" : "forwards" });
  });
  if (!to) setTimeout(done, DEAL_MS + APART_MS * (list.length - 1));
}

function SpreadView({ sp, members, nodes }) {
  const root = useRef(), closing = useRef(false);
  const member = members.find((m) => m.slug === sp.member);
  const cards = member ? columnOf(member, nodes).filter((x) => sp.keys.includes(keyOf(x.n, x.t))) : [];
  const goal = nodes.find((n) => n.slug === sp.goal);
  const move = (to, done) => dealCards(root.current, sp.from, to, done);              // each card from the stack's place to its own (to: true), or back

  useLayoutEffect(() => {                              // dealt once, when it opens
    move(true, () => {});
    gather = () => {
      if (closing.current) return;
      closing.current = true;
      move(false, () => { spread.value = null; });
    };
    return () => { gather = null; };
  }, []);
  useEffect(() => { if (!cards.length) spread.value = null; }, [cards.length]);          // its stack is gone

  const press = (e) => { if (!e.target.closest(".arena-spread__card, .ork-btn")) closeSpread(); };
  const line = `${goal?.short || goal?.title || ""}`;
  return html`<div ref=${root} class=${cls("arena-spread", { "is-gathering": closing.current })} role="group" aria-label=${`${line}: ${plural(cards.length, "task", "tasks")} of ${member?.name || ""} at this phase`} onClick=${press}>
    <span class="arena-spread__cap"><b>${line}</b> · ${plural(cards.length, "task", "tasks")} of ${member?.name || ""} at this phase</span>
    <div class="arena-spread__row">
      ${cards.map((x, i) => {
        const { n, t } = x, key = keyOf(n, t);
        const rl = relationOf(n, t);
        return html`<button type="button" key=${key} class=${cls("arena-task arena-spread__card", stateCls(n, t, rl, false))} data-spread-key=${key} data-task=${t.id} data-idea=${n.slug} data-state=${t.state}
          title=${cardTip(n, t)} aria-label=${`${t.title} (${n.title}): ${taskFoot(t, n)}`} onClick=${() => open(n, t)}
          onMouseEnter=${() => { taskHover.value = key; taskHoverBy.value = "pointer"; }} onMouseLeave=${() => { if (taskHover.value === key) taskHover.value = ""; }}
          onFocus=${() => { taskHover.value = key; taskHoverBy.value = "focus"; }} onBlur=${() => { if (taskHover.value === key) taskHover.value = ""; }}>
          <${CardBody} n=${n} t=${t} phase=${sp.row} deps=${depLines(n, t)} foot=${footParts(n, t, rl)} />
        </button>`;
      })}
    </div>
    <button type="button" class="ork-btn" onClick=${closeSpread}>Put them back</button>
  </div>`;
}

/** A deal over the window (spec 52 §3.4, §4.1): the scrim, the line over the cards (`cap`), the cards (`cards(gather)`: each a `.arena-spread__card`),
 *  *Put them back*. A `dialog` named `name`; the focus starts on the card `start`, ←/→ move between the cards, Enter or Space presses one. *Put them back*,
 *  Esc and a press on the scrim gather them (the deal backwards), then `done`, and the focus goes back to `back`. `gather(then)`: a card's press gathers
 *  them, then `then` (no focus back: what it opens takes it). */
export function Dealt({ name, cap, from, back, done, start = 0, cards, cls: more = "" }) {
  const root = useRef(), closing = useRef(false);
  const gather = (then) => {
    if (closing.current) return;
    closing.current = true;
    dealCards(root.current, from, false, () => {
      done();
      if (then) then();
      else if (back?.isConnected) back.focus();
    });
  };
  useLayoutEffect(() => {
    dealCards(root.current, from, true, () => {});
    const all = root.current.querySelectorAll(".arena-spread__card");
    (all[start] || all[0])?.focus();
    const key = (e) => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); gather(); } };
    window.addEventListener("keydown", key, true);
    return () => window.removeEventListener("keydown", key, true);
  }, []);
  const move = (e) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const all = [...root.current.querySelectorAll(".arena-spread__card")], at = all.indexOf(document.activeElement);
    if (at < 0) return;
    e.preventDefault();
    all[(at + (e.key === "ArrowRight" ? 1 : -1) + all.length) % all.length].focus();
  };
  const press = (e) => { if (!e.target.closest(".arena-spread__card, .ork-btn")) gather(); };
  return html`<div ref=${root} class=${cls("arena-spread arena-deal", more)} role="dialog" aria-modal="true" aria-label=${name} onClick=${press} onKeyDown=${move}>
    <span class="arena-spread__cap">${cap}</span>
    <div class="arena-spread__row">${cards(gather)}</div>
    <button type="button" class="ork-btn" onClick=${() => gather()}>Put them back</button>
  </div>`;
}

/** The open spread over the field, or nothing. Keyed by its stack, so another press deals again. */
export function Spread({ members, nodes }) {
  const sp = spread.value;
  return sp ? html`<${SpreadView} key=${`${sp.goal}/${sp.member}/${sp.row}`} sp=${sp} members=${members} nodes=${nodes} />` : null;
}
