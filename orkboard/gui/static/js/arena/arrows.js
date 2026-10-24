// The arrows (docs/specs/50-parties-and-goals.md §3.4): hovering a card (or a spread card) draws an arrow from each task it waits for to it and from it
// to each task that waits for it, between the cards that are shown — a dashed ink line, 2 px, with a head, over the field and under the drawer. An end
// that is not shown (a task under another card of its stack, or one the filter has taken away, or one scrolled out of its column) draws none. Only
// with a fine pointer (`(hover: hover)`); the keyboard's focus draws them too. The card's foot keeps the words (stacks.js `footParts`).
import { useLayoutEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { spread, taskHover, taskHoverBy } from "./arenastate.js";
import { waitersOf, waitsForOf } from "./arenawords.js";

const HEAD = 9;                                       // the arrow head's length in px

const fine = () => typeof matchMedia === "function" && matchMedia("(hover: hover)").matches;

/** Where the segment from the centre of `a` to the centre of `b` leaves `a`: the point on a's edge. */
function edgeOf(a, b) {
  const cx = a.x + a.w / 2, cy = a.y + a.h / 2, dx = b.x + b.w / 2 - cx, dy = b.y + b.h / 2 - cy;
  if (!dx && !dy) return { x: cx, y: cy };
  const k = Math.min(dx ? a.w / 2 / Math.abs(dx) : Infinity, dy ? a.h / 2 / Math.abs(dy) : Infinity);
  return { x: cx + dx * k, y: cy + dy * k };
}

/** The arrow from the box `a` to the box `b` (both {x, y, w, h} in the host's coordinates): its line, which stops short of the head, and the head's points. */
export function segment(key, a, b) {
  const p = edgeOf(a, b), q = edgeOf(b, a), ang = Math.atan2(q.y - p.y, q.x - p.x);
  const w = (d) => `${(q.x - HEAD * Math.cos(ang + d)).toFixed(1)},${(q.y - HEAD * Math.sin(ang + d)).toFixed(1)}`;
  return { key, x1: p.x, y1: p.y, x2: q.x - (HEAD - 1) * Math.cos(ang), y2: q.y - (HEAD - 1) * Math.sin(ang), head: `${q.x.toFixed(1)},${q.y.toFixed(1)} ${w(0.45)} ${w(-0.45)}` };
}

/** The svg layer that draws `lines` (from `segment`) over its positioned host. */
export function ArrowLines({ lines }) {
  return html`<svg class="arena-arrows" aria-hidden="true">${lines.map((l) => html`<g key=${l.key} class="arena-arrow" data-edge=${l.key}>
    <line x1=${l.x1} y1=${l.y1} x2=${l.x2} y2=${l.y2} /><polygon points=${l.head} /></g>`)}</svg>`;
}

/** The lines between the cards shown: [{x1, y1, x2, y2, head: "points"}]. `host`: the element the lines are drawn in. */
export function linesFor(host, nodes, hover, inSpread) {
  const slash = hover.lastIndexOf("/"), goal = hover.slice(0, slash), id = hover.slice(slash + 1);
  const n = nodes.find((x) => x.slug === goal), t = n?.tasks.find((x) => x.id === id);
  if (!n || !t) return [];
  const base = host.getBoundingClientRect(), attr = inSpread ? "data-spread-key" : "data-key";
  const rect = (task) => {                            // a card's box in the host's own coordinates; null when it is not shown
    const el = host.querySelector(`[${attr}="${CSS.escape(`${n.slug}/${task.id}`)}"]`);
    if (!el) return null;
    const r = el.getBoundingClientRect(), box = { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
    const clip = el.closest(".arena-stack, .arena-solo");           // a column scrolls inside itself: a card out of view is not shown
    if (clip) {
      const c = clip.getBoundingClientRect();
      if (r.bottom <= c.top || r.top >= c.bottom || r.right <= c.left || r.left >= c.right) return null;
    }
    return box;
  };
  const me = rect(t);
  if (!me) return [];
  const pairs = [...waitsForOf(n, t).map((s) => [s, t]), ...waitersOf(n, t).map((w) => [t, w])];
  const out = [];
  for (const [from, to] of pairs) {
    const a = from === t ? me : rect(from), b = to === t ? me : rect(to);
    if (!a || !b) continue;
    out.push(segment(`${from.id}>${to.id}`, a, b));
  }
  return out;
}

/** The arrows layer over `host` (the field's body). Redrawn when the hovered card or the cards change. */
export function Arrows({ host, nodes }) {
  const hover = taskHover.value, by = taskHoverBy.value, inSpread = !!spread.value;
  const [lines, setLines] = useState([]);
  useLayoutEffect(() => {
    const el = host.current;
    const on = !!hover && !!el && (by === "focus" || fine());
    const next = on ? linesFor(el, nodes, hover, inSpread) : [];
    setLines((was) => (was.length === 0 && next.length === 0 ? was : next));
  }, [hover, by, inSpread, nodes]);
  return html`<${ArrowLines} lines=${lines} />`;
}
