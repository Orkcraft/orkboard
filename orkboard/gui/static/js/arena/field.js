// The goal's field (docs/specs/49-one-window.md §5.3–§5.4, §11): a column per member of the party row, its open tasks running down
// from the member, two to a row — the top row lit, the rows below muted. A task is a small framed item; hovering one lights what
// waits for it. A member shown alone (solo) lays its tasks across the field's whole width in the same order. A task the field did
// not have a moment ago rises into its column, a merged one fades where it stands and the queue behind it steps up (motion.js).
import { useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Icon } from "../orkui.js";
import { showResult, showTask, showIdea, showPlan } from "../shell/store.js";
import { useColumn, useLit } from "./motion.js";
import { solo, ideaOn, ideaHover, taskHover, narrow } from "./arenastate.js";
import { columnOf, mergedBy, rowsOf, taskFoot, taskMark, waitersOf, plural } from "./arenawords.js";

const keyOf = (n, t) => `${n.slug}/${t.id}`;

/** One task: its wave, a mark, its idea (faint), its name, its state in words. `sign`: it is leaving (✓ merged, ✗ dropped) and fades where it
 *  stands; `quiet`: it is gone with no fade; `fresh`: it rises in (motion.js). */
export function TaskCard({ n, t, later = false, fresh = false, sign = "", quiet = false, wide = false }) {
  const hover = taskHover.value, src = hover === keyOf(n, t);
  const [hi, ht] = hover.split("/");
  const lit = hi === n.slug ? waitersOf(n, n.tasks.find((x) => x.id === ht) || { id: "" }) : [];
  const after = lit.some((x) => x.id === t.id);
  const hs = hi === n.slug && src ? waitersOf(n, t).length : 0;
  let foot = taskFoot(t, n);
  if (src && hs) foot = `→ ${hs} ${hs === 1 ? "waits" : "wait"} for it`;
  if (after) foot = `← waits for ${ht}`;
  const leaving = !!sign || quiet;
  const dim = (!!solo.value && solo.value !== t.by.slug && !wide) || (!!ideaOn.value && ideaOn.value !== n.slug);
  const mine = (ideaHover.value && ideaHover.value === n.slug) || (!!solo.value && solo.value === t.by.slug && !wide);
  const said = `${t.title} (${n.title}): ${taskFoot(t, n)}, wave ${t.wave}`;
  const tip = t.state === "failed" ? `${t.title} · ${t.error || "failed"}` : t.state === "held" ? `${t.title} · ${taskFoot(t, n)}` : `${t.title} · wave ${t.wave}${t.after?.length ? ` · after ${t.after.join(", ")}` : ""}`;
  const open = () => (t.state === "review" ? showResult(n.slug, t.id, { via: "map" }) : showTask(n.slug, t.id, { via: "map" }));
  const enter = () => { if (taskHover.value !== keyOf(n, t)) taskHover.value = keyOf(n, t); };
  const leave = () => { if (taskHover.value === keyOf(n, t)) taskHover.value = ""; };
  return html`<button type="button" class=${cls("arena-task", { "is-run": t.state === "running" || t.state === "testing", "is-review": t.state === "review", "is-next": t.state === "ready",
      "is-wait": t.state === "waiting" || t.state === "held", "is-fail": t.state === "failed", "is-dim": dim, "is-mine": mine, "is-later": later, "is-src": src && hs > 0,
      "is-after": after, "is-drawn": fresh, "is-leaving": !!sign, "is-gone": quiet })}
    data-key=${keyOf(n, t)} data-task=${t.id} data-idea=${n.slug} data-state=${t.state} data-wave=${t.wave} data-sign=${sign || undefined} title=${tip} aria-label=${said}
    aria-hidden=${leaving ? "true" : undefined} tabindex=${leaving ? -1 : undefined} onClick=${leaving ? undefined : open}
    onMouseEnter=${enter} onMouseLeave=${leave} onFocus=${enter} onBlur=${leave}>
    <span class="arena-task__top"><span class="arena-tbadge">${t.wave}</span><span class="arena-task__wave">wave</span>
      <span class="arena-task__mark">${taskMark(t)}${t.state === "held" && html`<${Icon} name="clock" />`}</span></span>
    <span class="arena-task__idea">${n.short || n.title}</span>
    <span class="arena-task__name">${t.short || t.title}</span>
    <span class="arena-task__foot">${foot}</span>
  </button>`;
}

/** The leader's items in Planning laid out as a column of its own (solo): a stop, a reading, a waiting idea. */
function PlanCard({ r, later }) {
  const open = () => (r.kind === "plan" ? showPlan(r.slug, "", { via: "map" }) : showIdea(r.slug, { via: "map" }));
  return html`<button type="button" class=${cls("arena-task", { "is-stop": r.stop, "is-run": r.busy && !r.stop, "is-wait": !r.stop && !r.busy, "is-later": later })} data-slug=${r.slug}
    title=${`${r.full} · ${r.words}`} aria-label=${`${r.full}: ${r.words}`} onClick=${open}>
    <span class="arena-task__top"><span class="arena-tbadge">${r.mark || "·"}</span><span class="arena-task__mark"></span></span>
    <span class="arena-task__idea">Planning</span><span class="arena-task__name">${r.title}</span><span class="arena-task__foot">${r.words}</span></button>`;
}

/** The sign a task that is gone leaves with: ✓ when it merged, ✗ when it was dropped, "" when it only went elsewhere. */
const signOf = (nodes) => (x) => {
  const t = nodes.find((n) => n.slug === x.n.slug)?.tasks.find((y) => y.id === x.t.id);
  return !t ? "" : t.state === "merged" ? "✓" : t.state === "dropped" ? "✗" : "";
};

/** A column's rows: [[entry, entry], …] from the member down; every row but the first muted. */
function Stack({ list, per, wide }) {
  return rowsOf(list, per).map((row, i) => html`<div key=${i} class=${cls("arena-srow", { "is-wide": wide })}>
    ${row.map((e) => html`<${TaskCard} key=${e.key} n=${e.it.n} t=${e.it.t} later=${i > 0} fresh=${e.fresh} sign=${e.sign} quiet=${e.quiet} wide=${wide} />`)}</div>`);
}

/** A member's column: its open tasks running down from it, *✓ k in dev* at its far end; what changes in it moves as motion.js says. */
function Column({ m, nodes, col }) {
  const ref = useRef(), done = useRef(), at = useRef(nodes);
  at.current = nodes;
  const list = useColumn(ref, col, (x) => keyOf(x.n, x.t), (x) => signOf(at.current)(x));
  const merged = mergedBy(m, nodes);
  useLit(done, merged);
  return html`<div ref=${ref} class=${cls("arena-stack", { "is-col": solo.value === m.slug })} role="group" data-agent=${m.slug}
    aria-label=${`${m.name}: ${plural(col.length, "task", "tasks")}, the one at work nearest the agent`}>
    ${!list.length && html`<span class="arena-stack__empty">No task now</span>`}
    <${Stack} list=${list} per=${2} wide=${false} />
    ${merged > 0 && html`<span ref=${done} class="arena-stack__done">✓ ${merged} in dev</span>`}
  </div>`;
}

/** The columns: the labels over the first builder and the first checker, a column per member. */
export function Columns({ members, nodes, cols }) {
  const first = {};
  const heads = members.map((m) => {
    const label = !first[m.band] ? (m.band === "build" ? "Implementation" : "Checking") : "";
    if (label) first[m.band] = true;
    return { key: m.slug, label };
  });
  return html`<div class="arena-cols" style=${`--cols:${cols}`}>
    <div class="arena-cols__head">${heads.map((h) => html`<span key=${h.key} class=${cls("arena-lbl", { "is-blank": !h.label })}>${h.label}</span>`)}</div>
    <div class="arena-cols__grid">
      ${!members.length && html`<p class="arena-cap arena-cols__none">No builder and no checker in this party. Edit the party in the bar above.</p>`}
      ${members.map((m) => html`<${Column} key=${m.slug} m=${m} nodes=${nodes} col=${columnOf(m, nodes)} />`)}
    </div>
  </div>`;
}

/** A member shown alone: its tasks (or the leader's Planning items) across the field's whole width, six to a row, in its column's order. */
export function Solo({ members, lead, nodes, planning }) {
  const m = [...members, lead].find((x) => x && x.slug === solo.value);
  if (!m) return null;
  const isLead = m === lead;
  return isLead ? html`<${SoloLead} m=${m} planning=${planning} />` : html`<${SoloColumn} m=${m} nodes=${nodes} />`;
}

function SoloHead({ m, title, n }) {
  return html`<div class="arena-solo__head"><h2 class="arena-lbl">${title}</h2><span class="ork-count">${n}</span><span class="arena-spacer"></span>
    <button type="button" class="ork-btn quiet" onClick=${() => { solo.value = ""; }}>Show everyone’s work</button></div>`;
}

function SoloLead({ m, planning }) {
  const items = [...planning.rows, ...planning.raw];
  return html`<div class="arena-solo-wrap"><${SoloHead} m=${m} title=${`Only ${m.name}’s work`} n=${items.length} />
    <div class="arena-solo" role="group" aria-label=${`Only ${m.name}’s work`} data-agent=${m.slug}>
      ${!items.length && html`<p class="arena-cap arena-solo__empty">Nothing in Planning.</p>`}
      ${rowsOf(items, narrow.value ? 3 : 6).map((row, i) => html`<div key=${i} class="arena-srow is-wide">${row.map((x) => html`<${PlanCard} key=${x.slug} r=${x} later=${i > 0} />`)}</div>`)}
    </div></div>`;
}

function SoloColumn({ m, nodes }) {
  const ref = useRef(), done = useRef(), at = useRef(nodes);
  at.current = nodes;
  const col = columnOf(m, nodes), merged = mergedBy(m, nodes);
  const list = useColumn(ref, col, (x) => keyOf(x.n, x.t), (x) => signOf(at.current)(x));
  useLit(done, merged);
  const title = `Only ${m.name}’s tasks`;
  return html`<div class="arena-solo-wrap"><${SoloHead} m=${m} title=${title} n=${col.length} />
    <div ref=${ref} class="arena-solo" role="group" aria-label=${title} data-agent=${m.slug}>
      ${!list.length && html`<p class="arena-cap arena-solo__empty">${m.name} has no task on this goal now.</p>`}
      <${Stack} list=${list} per=${narrow.value ? 3 : 6} wide=${true} />
      ${merged > 0 && html`<span ref=${done} class="arena-stack__done">✓ ${merged} in dev</span>`}
    </div></div>`;
}
