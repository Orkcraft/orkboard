// The ideas bar (docs/specs/49-one-window.md §4.2): the goal's one line — *Ideas at work n · Now: …*, the goal's numbers, About this
// goal, Edit the party. Open, it lists the ideas at work (title and price, the stage track, pips, a note); a click on one shows only
// its tasks and its results (pressed; a second click shows all), hovering it lights its tasks. Done (n) folds the done ideas.
import { html, cls } from "../html.js";
import { Chev } from "../orkui.js";
import { showGoal, gateData } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { soFarWords, planWords, inDevWords, pipsOf, STAGES, STAGE_WORDS, stageWords } from "../board/mapstage.js";
import { ideaOn, ideaHover, ideasOpen, doneOpen } from "./arenastate.js";
import { atWork, costWords, doneWords, ideaNote, leftWords, nowLine } from "./arenawords.js";

/** Planning — Implementation — Checking, the current one underlined, the past ones ✓, and the round once past 1. */
function Track({ n }) {
  const at = STAGES.indexOf(n.stage);
  return html`<span class="arena-track" aria-label=${`Stage: ${stageWords(n)}`}>${STAGES.map((s, i) => html`<span key=${s} class="arena-track__one">
      <span class=${cls("arena-track__stage", { "is-now": i === at, "is-past": i < at })} aria-current=${i === at ? "step" : undefined}>${i < at ? "✓ " : ""}${STAGE_WORDS[s]}</span>${i < 2 && html`<i aria-hidden="true"></i>`}</span>`)}
    ${n.round > 1 && html`<span class="arena-track__round">· round ${n.round}</span>`}</span>`;
}

function Row({ n, lead }) {
  const on = ideaOn.value === n.slug, note = ideaNote(n, lead);
  const cost = [soFarWords(n.usd), planWords(n.plan_estimate || n.estimate)].filter(Boolean).join(" · ");
  return html`<button type="button" class=${cls("arena-irow", { "is-on": on })} data-slug=${n.slug} aria-pressed=${on} title="A click shows only this idea’s tasks"
    onClick=${() => { ideaOn.value = on ? "" : n.slug; }}
    onMouseEnter=${() => { ideaHover.value = n.slug; }} onMouseLeave=${() => { if (ideaHover.value === n.slug) ideaHover.value = ""; }}
    onFocus=${() => { ideaHover.value = n.slug; }} onBlur=${() => { if (ideaHover.value === n.slug) ideaHover.value = ""; }}>
    <span class="arena-irow__main"><span class="arena-irow__title">${n.title}</span><span class="arena-cap">${cost}</span></span>
    <${Track} n=${n} />
    <span class="arena-irow__pips"><span class="ork-pips" aria-hidden="true">${pipsOf(n).map((p, i) => html`<i key=${i} class=${p === "done" ? "d" : p === "working" ? "w" : ""}></i>`)}</span>
      <span class="arena-irow__dev">${inDevWords(n)}</span></span>
    <span class=${cls("arena-irow__note", { "is-no": note.tone === "no" })}>${note.text}</span>
  </button>`;
}

export function IdeasBar({ g, nodes, lead, reading }) {
  const work = nodes.filter(atWork), done = nodes.filter((n) => n.state === "done" || n.stage === "done");
  const open = ideasOpen.value, line = nowLine(nodes, lead, reading);
  const gate = gateData.value;
  return html`<div class="arena-ibar">
    <div class="arena-ibar__bar">
      <button type="button" class="arena-ibar__head" aria-expanded=${open} onClick=${() => { ideasOpen.value = !open; }} title=${line}>
        <${Chev} dir=${open ? "up" : "down"} /><span class="arena-lbl">Ideas at work</span><span class="ork-count">${work.length}</span>
        <span class="arena-ibar__now"><span class="arena-muted">Now:</span> ${line}</span></button>
      <span class="arena-ibar__goal" title=${`done when ${(g.done_when || []).join(", ") || "—"}`}>${[leftWords(g, nodes), costWords(g)].filter(Boolean).join(" · ")}</span>
      <button type="button" class="ork-btn quiet" title="Done when, priority, the checks and the price of this goal" onClick=${() => showGoal(g.slug, { via: "map" })}>About this goal</button>
      <button type="button" class="ork-btn quiet" onClick=${() => openDialog("goal", { slug: g.slug })}>Edit the party</button>
    </div>
    ${open && html`<div class="arena-ibar__list">
      ${!work.length && html`<p class="arena-cap">No idea is at work. A plan you start comes here.</p>`}
      ${work.map((n) => html`<${Row} key=${n.slug} n=${n} lead=${lead} />`)}
      <button type="button" class="ork-btn quiet arena-ibar__done" aria-expanded=${doneOpen.value} onClick=${() => { doneOpen.value = !doneOpen.value; }}>Done (${done.length})</button>
      ${doneOpen.value && html`<ul class="arena-done">${done.map((n) => html`<li key=${n.slug}><span class="arena-ok">✓</span> ${n.title} <span class="arena-cap">· ${doneWords(n, gate)}</span></li>`)}</ul>`}
    </div>`}
  </div>`;
}
