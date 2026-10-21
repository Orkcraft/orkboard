// The goal's field (docs/specs/49-one-window.md §5.3–§5.4, §11): a column per member of the party row, its open tasks rising bottom-up
// from the member, two to a row — the bottom row lit, the rows above muted. A task is a small framed item; hovering one lights what
// waits for it. A member shown alone (solo) lays its tasks across the field's whole width in the same order. A task the field did
// not have a moment ago rises into its column (not on the first read), a merged one leaves once (mapghost.js).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Icon } from "../orkui.js";
import { showResult, showTask, showIdea, showPlan } from "../shell/store.js";
import { useLeaving } from "../board/mapghost.js";
import { solo, ideaOn, ideaHover, taskHover, narrow } from "./arenastate.js";
import { atWork, columnOf, mergedBy, rowsOf, taskFoot, taskMark, waitersOf, plural } from "./arenawords.js";

const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const keyOf = (n, t) => `${n.slug}/${t.id}`;

/** The keys the field did not have a moment ago (none on the first read: the hook is mounted with the goal). */
function useDrawn(keys) {
  const seen = useRef(null);
  const [fresh, setFresh] = useState([]);
  const sig = keys.join("|");
  useEffect(() => {
    if (seen.current === null) { seen.current = new Set(keys); return undefined; }
    const add = keys.filter((k) => !seen.current.has(k));
    keys.forEach((k) => seen.current.add(k));
    if (!add.length || reducedMotion()) return undefined;
    setFresh(add);
    const timer = setTimeout(() => setFresh([]), 450);
    return () => clearTimeout(timer);
  }, [sig]);
  return fresh;
}

/** One task: its wave, a mark, its idea (faint), its name, its state in words. */
export function TaskCard({ n, t, later = false, fresh = false, leaving = false, wide = false }) {
  const hover = taskHover.value, src = hover === keyOf(n, t);
  const [hi, ht] = hover.split("/");
  const lit = hi === n.slug ? waitersOf(n, n.tasks.find((x) => x.id === ht) || { id: "" }) : [];
  const after = lit.some((x) => x.id === t.id);
  const hs = hi === n.slug && src ? waitersOf(n, t).length : 0;
  let foot = leaving ? "in dev" : taskFoot(t, n);
  if (src && hs) foot = `→ ${hs} ${hs === 1 ? "waits" : "wait"} for it`;
  if (after) foot = `← waits for ${ht}`;
  const dim = (!!solo.value && solo.value !== t.by.slug && !wide) || (!!ideaOn.value && ideaOn.value !== n.slug);
  const mine = (ideaHover.value && ideaHover.value === n.slug) || (!!solo.value && solo.value === t.by.slug && !wide);
  const said = `${t.title} (${n.title}): ${taskFoot(t, n)}, wave ${t.wave}`;
  const tip = t.state === "failed" ? `${t.title} · ${t.error || "failed"}` : t.state === "held" ? `${t.title} · ${taskFoot(t, n)}` : `${t.title} · wave ${t.wave}${t.after?.length ? ` · after ${t.after.join(", ")}` : ""}`;
  const open = () => (t.state === "review" ? showResult(n.slug, t.id, { via: "map" }) : showTask(n.slug, t.id, { via: "map" }));
  const enter = () => { if (taskHover.value !== keyOf(n, t)) taskHover.value = keyOf(n, t); };
  const leave = () => { if (taskHover.value === keyOf(n, t)) taskHover.value = ""; };
  return html`<button type="button" class=${cls("arena-task", { "is-run": t.state === "running" || t.state === "testing", "is-review": t.state === "review", "is-next": t.state === "ready",
      "is-wait": t.state === "waiting" || t.state === "held", "is-fail": t.state === "failed", "is-dim": dim, "is-mine": mine, "is-later": later, "is-src": src && hs > 0,
      "is-after": after, "is-drawn": fresh, "map-leaving": leaving })}
    data-task=${t.id} data-idea=${n.slug} data-state=${t.state} data-wave=${t.wave} title=${tip} aria-label=${said} aria-hidden=${leaving ? "true" : undefined}
    tabindex=${leaving ? -1 : undefined} onClick=${leaving ? undefined : open} onMouseEnter=${enter} onMouseLeave=${leave} onFocus=${enter} onBlur=${leave}>
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

/** A column's rows: [[item, item], …] from the member up; every row but the first muted. */
function Stack({ rows, wide, render }) {
  return rows.map((row, i) => html`<div key=${i} class=${cls("arena-srow", { "is-wide": wide })}>${row.map((x) => render(x, i > 0))}</div>`);
}

/** The columns: the labels over the first builder and the first checker, a column per member, a free seat's narrow and hatched. */
export function Columns({ g, members, nodes, cols }) {
  const live = nodes.filter(atWork);
  const all = live.flatMap((n) => n.tasks.filter((t) => t.state !== "merged" && t.state !== "dropped").map((t) => ({ n, t })));
  const fresh = useDrawn(all.map((x) => keyOf(x.n, x.t)));
  const ghosts = useLeaving(all, (x) => keyOf(x.n, x.t), (x) => nodes.find((n) => n.slug === x.n.slug)?.tasks.find((t) => t.id === x.t.id)?.state === "merged");
  const first = {};
  const heads = members.map((m) => {
    const label = !m.free && !first[m.band] ? (m.band === "build" ? "Implementation" : "Checking") : "";
    if (label) first[m.band] = true;
    return { key: m.slug, label };
  });
  return html`<div class="arena-cols" style=${`--cols:${cols}`}>
    <div class="arena-cols__head">${heads.map((h) => html`<span key=${h.key} class=${cls("arena-lbl", { "is-blank": !h.label })}>${h.label}</span>`)}</div>
    <div class="arena-cols__grid">
      ${members.map((m) => {
        if (m.free) return html`<div key=${m.slug} class="arena-stack is-free" role="group" aria-label="A free seat" data-band=${m.band}></div>`;
        const col = columnOf(m, nodes), gone = ghosts.filter((x) => x.t.by.slug === m.slug && !col.some((c) => keyOf(c.n, c.t) === keyOf(x.n, x.t)));
        const list = [...col.map((c) => ({ ...c, leaving: false })), ...gone.map((c) => ({ ...c, leaving: true }))];
        const merged = mergedBy(m, nodes);
        return html`<div key=${m.slug} class=${cls("arena-stack", { "is-col": solo.value === m.slug })} role="group" data-agent=${m.slug}
          aria-label=${`${m.name}: ${plural(col.length, "task", "tasks")}, the one at work nearest the agent`}>
          ${!list.length && html`<span class="arena-stack__empty">No task now</span>`}
          <${Stack} rows=${rowsOf(list, 2)} wide=${false}
            render=${(x, later) => html`<${TaskCard} key=${keyOf(x.n, x.t) + (x.leaving ? "gone" : "")} n=${x.n} t=${x.t} later=${later} leaving=${x.leaving} fresh=${fresh.includes(keyOf(x.n, x.t))} />`} />
          ${merged > 0 && html`<span class="arena-stack__done">✓ ${merged} in dev</span>`}
        </div>`;
      })}
    </div>
  </div>`;
}

/** A member shown alone: its tasks (or the leader's Planning items) across the field's whole width, six to a row, in its column's order. */
export function Solo({ g, members, lead, nodes, planning }) {
  const m = [...members, lead].find((x) => x && x.slug === solo.value);
  if (!m) return null;
  const isLead = m === lead;
  const col = isLead ? [] : columnOf(m, nodes);
  const items = isLead ? [...planning.rows, ...planning.raw] : col;
  const per = narrow.value ? 3 : 6;
  const title = isLead ? `Only ${m.name}’s work` : `Only ${m.name}’s tasks`;
  const merged = isLead ? 0 : mergedBy(m, nodes);
  return html`<div class="arena-solo-wrap">
    <div class="arena-solo__head"><h2 class="arena-lbl">${title}</h2><span class="ork-count">${items.length}</span><span class="arena-spacer"></span>
      <button type="button" class="ork-btn quiet" onClick=${() => { solo.value = ""; }}>Show everyone’s work</button></div>
    <div class="arena-solo" role="group" aria-label=${title} data-agent=${m.slug}>
      ${!items.length && html`<p class="arena-cap arena-solo__empty">${isLead ? "Nothing in Planning." : `${m.name} has no task on this goal now.`}</p>`}
      <${Stack} rows=${rowsOf(items, per)} wide=${true}
        render=${(x, later) => (isLead ? html`<${PlanCard} key=${x.slug} r=${x} later=${later} />` : html`<${TaskCard} key=${keyOf(x.n, x.t)} n=${x.n} t=${x.t} later=${later} wide=${true} />`)} />
      ${merged > 0 && html`<span class="arena-stack__done">✓ ${merged} in dev</span>`}
    </div>
  </div>`;
}
