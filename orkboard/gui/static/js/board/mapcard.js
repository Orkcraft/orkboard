// The idea's card (docs/specs/48-map-ideas.md §5): on the right of an expanded idea, in orkUI's double frame. It shows the title, the
// stage, the pips, how many tasks are in dev, the cost and the plan's estimate; in Planning with a plan waiting it starts the work; in
// Implementation and Checking it holds the idea's results (Merge into dev · Send back · Drop, Review's own answers). No branch per idea
// and no merge into main: the dev → main gate stays in Needs you.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { review, act, showPlan, showResult } from "../shell/store.js";
import { ResultActions, Found, testsWords, changesWords, usd } from "../shell/review.js";
import { nodeView } from "./maplayout.js";
import { stageWords, inDevWords, planWords, soFarWords, pipsOf } from "./mapstage.js";
import { useLeaving } from "./mapghost.js";

const RESULTS = 3;                       // the results listed on one card, the rest as *and n more*

/** One result waiting for the person: what it is, its tests, its changes and cost, and the three answers. */
function Result({ r, leaving = false }) {
  const t = testsWords(r);
  return html`<li class=${cls("map-result", { "map-leaving": leaving })} data-task=${r.task} aria-hidden=${leaving ? "true" : undefined}>
    <button type="button" class="map-result__open" title="Open the result: its code" onClick=${() => showResult(r.idea, r.task, { via: "map" })}>
      <b>${r.title}</b>${r.round > 1 ? html` <span class="shell-round">round ${r.round}</span>` : ""}</button>
    <dl class="shell-facts">
      <dt>Tests</dt><dd class=${`is-${t.tone}`}>${t.mark} ${t.text}${t.names.length ? html` <span class="ok-tone-muted">${t.names.join(", ")}</span>` : ""}</dd>
      <dt>Changes</dt><dd>${changesWords(r.diff)}</dd>
      ${r.cost != null && html`<dt>Cost</dt><dd>${usd(r.cost)}</dd>`}
    </dl>
    ${leaving ? html`<span class="map-result__gone">merged into ${review.value?.into || "dev"}</span>` : html`<${Found} r=${r} />
      ${r.conflict && html`<p class="ok-tone-error shell-conflict">⚠ ${r.conflict}</p>`}<${ResultActions} r=${r} />`}
  </li>`;
}

/** The results of the idea; one that was merged a moment ago folds out once (§5.3). */
function Waiting({ n }) {
  const results = n.results || [];
  const [all, setAll] = useState(false);
  const gone = useLeaving(results, (r) => r.task, (r) => n.tasks.find((t) => t.id === r.task)?.state === "merged");
  const shown = all ? results : results.slice(0, RESULTS);
  return html`<div class="map-card__waits" aria-label="Waits for your look">
    <span class="ok-font-label">Waits for your look</span>
    ${(shown.length || gone.length) ? html`<ul class="map-results">${shown.map((r) => html`<${Result} key=${r.task} r=${r} />`)}
      ${gone.map((r) => html`<${Result} key=${"gone" + r.task} r=${r} leaving />`)}</ul>` : html`<p class="ok-tone-muted">Nothing waits for your look.</p>`}
    ${results.length > RESULTS && html`<button type="button" class="board-link map-card__more" aria-expanded=${all} onClick=${() => setAll(!all)}>${all ? "fewer" : `and ${results.length - RESULTS} more`}</button>`}
  </div>`;
}

/** Planning with a plan waiting: Start the work (the plan's pass; autostart stays), Open the plan; held for the night: Start now. */
function PlanActions({ n }) {
  const night = n.start_at === "night";
  return html`<div class="map-card__actions">
    ${night ? html`<button class="ork-btn primary" onClick=${() => act("ideas.start_now", { slug: n.slug, via: "map" })}>Start now</button>`
      : html`<button class="ork-btn primary" onClick=${() => act("ideas.start", { slug: n.slug, via: "map" })}>Start the work</button>`}
    <button class="ork-btn" onClick=${() => showPlan(n.slug, "", { via: "map" })}>Open the plan</button>
  </div>`;
}

export function IdeaCard({ n, titles }) {
  const v = nodeView(n, titles);
  const waiting = n.state === "plan" && n.needs_you === "plan" && n.stage === "planning";
  const heldPlan = n.state === "plan" && n.start_at === "night";
  const midway = n.stage === "implementation" || n.stage === "checking";
  const cost = [soFarWords(n.usd), planWords(n.plan_estimate || n.estimate)].filter(Boolean).join(" · ");
  return html`<aside class="map-card-frame" aria-label=${`${n.title}: stage, cost and results`} data-slug=${n.slug}>
    <b class="map-card-frame__title">${n.title}</b>
    <span class="ok-font-status ok-tone-muted">${stageWords(n)}</span>
    ${n.tasks.length > 0 && html`<span class="map-card-frame__pips ok-font-status"><span class="map-pips-row" aria-hidden="true">${pipsOf(n).map((p, i) => html`<i key=${i} class="map-pip" data-pip=${p}></i>`)}</span>
      ${inDevWords(n)}</span>`}
    ${cost && html`<span class="ok-font-status ok-tone-muted">${cost}</span>`}
    ${v.wait && html`<span class="ok-font-status ok-tone-muted map-card-frame__wait">${v.wait}</span>`}
    ${(waiting || heldPlan) && n.stage === "planning" && html`<${PlanActions} n=${n} />`}
    ${midway && html`<${Waiting} n=${n} />`}
    ${!midway && !waiting && !heldPlan && (n.results || []).length > 0 && html`<${Waiting} n=${n} />`}
  </aside>`;
}

