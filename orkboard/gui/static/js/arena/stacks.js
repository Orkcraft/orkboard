// A member's open tasks as cards in stacks, in rows by phase (docs/specs/50-parties-and-goals.md §3.4): under the member, its tasks lie in rows —
// *now* (a task at its goal's current wave), *next* (one wave after), *later* —, in a row one stack per goal (the goals in the Board's order),
// the front card first (at work, failed, in Review, ready, waiting, tonight), behind it one or two edges and ×n when there are more. A card is 5:7:
// the goal's element top left, its mark top right, the goal's short name, the task's name, its foot. A press on a stack of one opens the
// task (its result in Review), on a stack of more spreads it (spread.js); hovering a card draws what it waits for and what waits for it (arrows.js).
// What the member's rows do as tasks come and go is motion.js's (a column's `useColumn`).
import { html, cls } from "../html.js";
import { Elem, Sign } from "../orkui.js";
import { showResult, showTask } from "../shell/store.js";
import { taskHover, taskHoverBy, spread } from "./arenastate.js";
import { rowsOf, taskFoot, taskMark, waitersOf, waitsForOf } from "./arenawords.js";
import { elementOf } from "./goalwords.js";

export const keyOf = (n, t) => `${n.slug}/${t.id}`;
const MARKS = { work: "at work", cross: "failed", night: "tonight" };

/** What a task's hover says to a card: it is the one hovered (*src*, with what waits for it), one that waits for it (*after*) or one it waits for (*before*). */
export function relationOf(n, t) {
  const hover = taskHover.value;
  if (!hover) return { src: false, after: false, before: false, hovered: null };
  const [goal, id] = [hover.slice(0, hover.lastIndexOf("/")), hover.slice(hover.lastIndexOf("/") + 1)];
  if (goal !== n.slug) return { src: false, after: false, before: false, hovered: null };
  const h = n.tasks.find((x) => x.id === id);
  if (!h) return { src: false, after: false, before: false, hovered: null };
  return { src: h.id === t.id, after: waitersOf(n, h).some((x) => x.id === t.id), before: waitsForOf(n, h).some((x) => x.id === t.id), hovered: h };
}

/** A card's foot: its state in words; under a hover the words of the dependency (*<before> waits for <short>*, *<after> n wait for it*). Parts: [{sign, text}]. */
export function footParts(n, t, rel) {
  const rest = { sign: "", text: taskFoot(t, n) };
  const mine = waitersOf(n, t).length;
  if (rel.src && mine) return [{ sign: "after", text: `${mine} ${mine === 1 ? "waits" : "wait"} for it` }];
  if (rel.after) return [{ sign: "before", text: `waits for ${rel.hovered.short || rel.hovered.title}` }];
  if (rel.before && mine) return [{ sign: "after", text: `${mine} ${mine === 1 ? "waits" : "wait"} for it` }];
  return [rest];
}
export const Foot = ({ parts }) => parts.map((p, i) => html`<span key=${i} class="arena-task__line">${p.sign && html`<${Sign} name=${p.sign} /> `}${p.text}</span>`);

/** The tooltip of a card: its title and what it says of its state. */
export function cardTip(n, t) {
  const foot = taskFoot(t, n);
  return t.state === "failed" ? `${t.title} · ${t.error || "failed"}` : t.state === "held" ? `${t.title} · ${foot}` : `${t.title} · wave ${t.wave}${t.after?.length ? ` · after ${t.after.join(", ")}` : ""}`;
}

const open = (n, t) => (t.state === "review" ? showResult(n.slug, t.id, { via: "map" }) : showTask(n.slug, t.id, { via: "map" }));

/** The look of a card (shared by a stack's front and a spread's): the element, the mark, the goal, the name. `phase`: the spread's word over the name. */
export function CardBody({ n, t, phase = "", foot, deps = [], many = 0 }) {
  const el = elementOf(n), mark = taskMark(t, n);
  return html`<span class="arena-task__top"><${Elem} name=${el.name} dim=${el.dim} />${phase && html`<span class="arena-task__phase">${phase}</span>`}
      <span class="arena-task__mark" title=${MARKS[mark] || undefined}>${mark && html`<${Sign} name=${mark} />`}</span></span>
    <span class="arena-task__goal">${n.short || n.title}</span>
    <span class="arena-task__name">${t.short || t.title}</span>
    ${deps.length > 0 && html`<span class="arena-task__deps">${deps.map((d, i) => html`<span key=${i}><${Sign} name=${d.sign} /> ${d.text}</span>`)}</span>`}
    <span class="arena-task__foot"><${Foot} parts=${foot} /></span>
    ${many > 1 && html`<span class="arena-stk__n">×${many}</span>`}`;
}

/** The classes a card wears for its task's state and what the hover says of it. */
export const stateCls = (n, t, rel, later) => ({ "is-run": t.state === "running" || t.state === "testing", "is-review": t.state === "review", "is-next": t.state === "ready",
  "is-wait": t.state === "waiting" || t.state === "held", "is-fail": t.state === "failed", "is-later": later, "is-src": rel.src && waitersOf(n, t).length > 0,
  "is-after": rel.after, "is-before": rel.before });

/** One stack: the front card, edges behind it and ×n. `items`: the stack's entries as the column shows them ([{it: {n, t}, key, sign, quiet, fresh}]),
 *  the front first; a stack of more than one live card spreads on a press, a stack of one opens its task. */
function Stack({ goal, items, later, wide, member, row }) {
  const shown = items.filter((x) => !x.quiet), front = shown[0];
  if (!front) return null;
  const { n, t } = front.it, live = shown.filter((x) => !x.sign).length;
  const rel = relationOf(n, t), leaving = !!front.sign;
  const foot = footParts(n, t, rel), edges = Math.min(2, shown.length - 1);
  const enter = () => { if (taskHover.value !== front.key) taskHover.value = front.key; taskHoverBy.value = "pointer"; };
  const focus = () => { taskHover.value = front.key; taskHoverBy.value = "focus"; };
  const leave = () => { if (taskHover.value === front.key) taskHover.value = ""; };
  const press = (e) => {
    if (leaving) return;
    if (live > 1) spread.value = { goal, member, row, keys: shown.filter((x) => !x.sign).map((x) => x.key), from: e.currentTarget.getBoundingClientRect() };
    else open(n, t);
  };
  const said = `${t.title} (${n.title}): ${taskFoot(t, n)}, wave ${t.wave}${live > 1 ? `, and ${live - 1} more of this goal: a press shows them all` : ""}`;
  return html`<div class=${cls("arena-stk", { "is-many": live > 1, "is-fail": t.state === "failed", "is-wide": wide })} data-goal=${goal} data-n=${live}>
    ${Array.from({ length: edges }, (_, i) => html`<i key=${i} class="arena-stk__edge" style=${`left:${(i + 1) * 4}px;top:${-(i + 1) * 4}px`}></i>`)}
    <button type="button" class=${cls("arena-task", { ...stateCls(n, t, rel, later), "is-drawn": front.fresh, "is-leaving": !!front.sign, "is-gone": front.quiet, "has-n": live > 1 })}
      data-key=${front.key} data-task=${t.id} data-idea=${n.slug} data-state=${t.state} data-wave=${t.wave} data-sign=${front.sign || undefined} title=${cardTip(n, t)} aria-label=${said}
      aria-hidden=${leaving ? "true" : undefined} tabindex=${leaving ? -1 : undefined} onClick=${press}
      onMouseEnter=${enter} onMouseLeave=${leave} onFocus=${focus} onBlur=${leave}>
      <${CardBody} n=${n} t=${t} foot=${foot} many=${live} />
      ${leaving && html`<span class="arena-task__flash">${front.sign !== "fade" && html`<${Sign} name=${front.sign} big=${true} />`}</span>`}
    </button>
  </div>`;
}

/** A member's rows by phase: the label over each row's left edge (*now*, *next*, *later*), the rows after *now* muted. `list`: what `useColumn` shows. */
export function Rows({ list, nodes, member, wide = false }) {
  return rowsOf(list, nodes).map((r) => html`<div key=${r.row} class=${cls("arena-phase", { "is-later": r.row !== "now", "is-wide": wide })} data-row=${r.row}>
    <span class="arena-phase__lbl">${r.row}</span>
    ${r.stacks.map((s) => html`<${Stack} key=${s.goal} goal=${s.goal} items=${s.items} later=${r.row !== "now"} wide=${wide} member=${member} row=${r.row} />`)}
  </div>`);
}
