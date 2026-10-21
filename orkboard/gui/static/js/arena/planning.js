// Planning (docs/specs/49-one-window.md §4.3–§4.4): the left column's top, the goal's ideas in stage planning that are not new — the
// stops first, each a plain row (a mark, its title, its state in words, a plan's price) — and New (n) folded under them; its foot is
// the leader, with Process now. A click on a row opens it in the drawer.
import { html, cls } from "../html.js";
import { act, showIdea, showPlan } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { solo, rawOpen } from "./arenastate.js";
import { powerOf } from "./arenawords.js";
import { Member } from "./members.js";

function Row({ r, dim }) {
  const open = () => (r.kind === "plan" ? showPlan(r.slug, "", { via: "map" }) : showIdea(r.slug, { via: "map" }));
  return html`<button type="button" class=${cls("arena-prow", { "is-stop": r.stop, "is-dim": dim })} data-slug=${r.slug} data-state=${r.stop ? "stop" : r.busy ? "work" : "idle"}
    title=${`${r.full} · ${r.words}`} onClick=${open}>
    <span class=${cls("arena-prow__mark", { "is-alert": r.stop })} aria-hidden="true">${r.mark}</span>
    <span class="arena-prow__body"><span class="arena-prow__title">${r.title}</span><span class=${cls("arena-prow__state", { "is-alert": r.stop })}>${r.words}</span></span>
    ${r.cost && html`<span class="arena-prow__cost">${r.cost}</span>`}
  </button>`;
}

export function Planning({ g, nodes, planning, lead }) {
  const dim = !!solo.value && solo.value !== g.leader?.slug && solo.value !== lead?.slug;
  const power = powerOf(planning.raw, lead?.name || "Taskmaster");
  return html`<section class="arena-left" aria-label="Planning">
    <div class="arena-left__head">
      <h2 class="arena-lbl">Planning</h2><span class="ork-count">${planning.rows.length}</span><span class="arena-spacer"></span>
      <button type="button" class="ork-btn primary" onClick=${() => openDialog("idea", { goal: g.slug })}>+ New idea</button>
    </div>
    <div class="arena-deck">
      ${!planning.rows.length && !planning.raw.length && html`<p class="arena-cap">Nothing in Planning. A new idea starts here.</p>`}
      ${planning.rows.map((r) => html`<${Row} key=${r.slug} r=${r} dim=${dim} />`)}
      ${planning.raw.length > 0 && html`<button type="button" class="ork-btn quiet arena-raw" aria-expanded=${rawOpen.value} onClick=${() => { rawOpen.value = !rawOpen.value; }}>New (${planning.raw.length})</button>`}
      ${rawOpen.value && planning.raw.map((r) => html`<${Row} key=${r.slug} r=${r} dim=${dim} />`)}
    </div>
    <div class="arena-hero">
      ${lead && html`<${Member} m=${lead} nodes=${nodes} planning=${planning} lead=${true} />`}
      <button type="button" class="ork-btn arena-power" disabled=${power.off} title=${power.tip}
        onClick=${() => act("ideas.queue", { slug: power.slug, queue: "now", via: "party" })}>Process now · ${power.words}</button>
    </div>
  </section>`;
}
