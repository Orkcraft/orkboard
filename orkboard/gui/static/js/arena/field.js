// The party's field (docs/specs/49-one-window.md §5.3–§5.4, §11, docs/specs/50-parties-and-goals.md §3.4–§3.5): a column per member of the party row;
// under the member its open tasks lie in rows by phase, a stack per goal in a row (stacks.js). The goals the filter takes away leave (motion.js, without
// a check), a member with none says *Nothing of these goals*. A member shown alone (solo) lays its rows across the field's whole width. A task the field
// did not have a moment ago rises into its place (dealt from the stop of a plan just started, spec 57), a merged one fades where it stands and the rest settles (motion.js).
// The cards the stop that is looked at is about wear a ring (spec 58): stacks.js `linkedTo`, and a Planning card here.
import { useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Elem, Sign } from "../orkui.js";
import { showIdea, showPlan } from "../shell/store.js";
import { useColumn, useLit } from "./motion.js";
import { solo, stopAbout, stopLook } from "./arenastate.js";
import { columnOf, mergedBy, plural } from "./arenawords.js";
import { elementOf, inFilter, leaveOf } from "./goalwords.js";
import { Rows, goalWords, keyOf, typeSign } from "./stacks.js";

/** A member's column: its rows by phase running down from it, *<check> k in dev* at its far end; what changes in it moves as motion.js says. */
function Column({ m, nodes, col, shown }) {
  const ref = useRef(), done = useRef(), at = useRef({ nodes, shown });
  at.current = { nodes, shown };
  const list = useColumn(ref, col, (x) => keyOf(x.n, x.t), (x) => leaveOf(at.current.nodes, at.current.shown, x.n.slug, x.t.id), true);
  const merged = mergedBy(m, nodes);
  useLit(done, merged);
  return html`<div ref=${ref} class=${cls("arena-stack", { "is-col": solo.value === m.slug })} role="group" data-agent=${m.slug}
    aria-label=${`${m.name}: ${plural(col.length, "task", "tasks")}, the one at work nearest the agent`}>
    ${!list.length && html`<span class="arena-stack__empty">${shown.length ? "Nothing of these goals" : "No task now"}</span>`}
    <${Rows} list=${list} nodes=${nodes} member=${m.slug} />
    ${merged > 0 && html`<span ref=${done} class="arena-stack__done"><${Sign} name="check" /> ${merged} in dev</span>`}
  </div>`;
}

/** The columns: the labels over the first builder and the first checker, a column per member. `shown`: the goals the filter shows ([] for all). */
export function Columns({ members, nodes, cols, shown }) {
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
      ${members.map((m) => html`<${Column} key=${m.slug} m=${m} nodes=${nodes} col=${columnOf(m, nodes).filter((x) => inFilter(shown, x.n.slug))} shown=${shown} />`)}
    </div>
  </div>`;
}

/** A member shown alone: its rows by phase across the field's whole width, the leader's Planning goals the same way. */
export function Solo({ members, lead, nodes, planning, shown }) {
  const m = [...members, lead].find((x) => x && x.slug === solo.value);
  if (!m) return null;
  return m === lead ? html`<${SoloLead} m=${m} planning=${planning} />` : html`<${SoloColumn} m=${m} nodes=${nodes} shown=${shown} />`;
}

function SoloHead({ title, n }) {
  return html`<div class="arena-solo__head"><h2 class="arena-lbl">${title}</h2><span class="ork-count">${n}</span><span class="arena-spacer"></span>
    <button type="button" class="ork-btn quiet" onClick=${() => { solo.value = ""; }}>Show everyone’s work</button></div>`;
}

/** A Planning goal of the leader's, as a card: its element, what it is doing, its name, its words. */
function PlanCard({ r }) {
  const open = () => (r.kind === "plan" ? showPlan(r.slug, "", { via: "map" }) : showIdea(r.slug, { via: "map" }));
  const el = elementOf(r.node), named = goalWords({ title: r.full, type: r.node?.type });
  const linked = !!stopLook.value && stopAbout.value?.idea === r.slug;                        // the stop looked at is about this goal (spec 58 §1)
  return html`<div class=${cls("arena-stk", { "is-linked": linked })}><button type="button" class=${cls("arena-task", { "is-linked": linked, "is-stop": r.stop, "is-run": r.busy && !r.stop, "is-wait": !r.stop && !r.busy })} data-slug=${r.slug}
    title=${`${named} · ${r.words}`} aria-label=${`${named}: ${r.words}`} onClick=${open}>
    <span class="arena-task__top"><${Elem} name=${el.name} dim=${el.dim} />${typeSign(r.node)}</span>
    <span class="arena-task__goal">${r.node?.type?.name || "Planning"}</span><span class="arena-task__name">${r.title}</span><span class="arena-task__foot">${r.words}</span></button></div>`;
}

function SoloLead({ m, planning }) {
  const items = [...planning.rows, ...planning.raw];
  return html`<div class="arena-solo-wrap"><${SoloHead} title=${`Only ${m.name}’s work`} n=${items.length} />
    <div class="arena-solo" role="group" aria-label=${`Only ${m.name}’s work`} data-agent=${m.slug}>
      ${!items.length && html`<p class="arena-cap arena-solo__empty">Nothing in Planning.</p>`}
      <div class="arena-phase is-wide">${items.map((x) => html`<${PlanCard} key=${x.slug} r=${x} />`)}</div>
    </div></div>`;
}

function SoloColumn({ m, nodes, shown }) {
  const ref = useRef(), done = useRef(), at = useRef({ nodes, shown });
  at.current = { nodes, shown };
  const col = columnOf(m, nodes).filter((x) => inFilter(shown, x.n.slug)), merged = mergedBy(m, nodes);
  const list = useColumn(ref, col, (x) => keyOf(x.n, x.t), (x) => leaveOf(at.current.nodes, at.current.shown, x.n.slug, x.t.id), true);
  useLit(done, merged);
  const title = `Only ${m.name}’s tasks`;
  return html`<div class="arena-solo-wrap"><${SoloHead} title=${title} n=${col.length} />
    <div ref=${ref} class="arena-solo" role="group" aria-label=${title} data-agent=${m.slug}>
      ${!list.length && html`<p class="arena-cap arena-solo__empty">${shown.length ? "Nothing of these goals" : `${m.name} has no task in this party now.`}</p>`}
      <${Rows} list=${list} nodes=${nodes} member=${m.slug} wide=${true} />
      ${merged > 0 && html`<span ref=${done} class="arena-stack__done"><${Sign} name="check" /> ${merged} in dev</span>`}
    </div></div>`;
}
