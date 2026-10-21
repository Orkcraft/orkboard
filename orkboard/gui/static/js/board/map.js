// The Map (docs/specs/48-map-ideas.md, decisions §61): one goal at a time. Its header is the goal — title, priority, state, how far it
// is, *n of m ideas done*, *done when*, what it cost, today's merges — with a picker for another goal; under it one line with the whole
// party and each member's state; then the goal's ideas in trail order: the ones at work or waiting for the person expanded
// (mapidea.js: the stage track, the lanes, the waves, the idea's card), the rest one line each, the done ones folded into *Done (n)*.
// A view of `ideas.map`; its actions are the idea's card's (mapcard.js), the Board's own commands.
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Icon, WhoHead } from "../orkui.js";
import { PRIORITY_WORDS, track } from "./store.js";
import { mapData, mapSince, mapUi, mapView, review } from "../shell/store.js";
import { Cards } from "./cards.js";
import { openDialog } from "../shell/modals.js";
import { keepGoal, keptGoal } from "./tracks.js";
import { goalState, progressOf, spentWords, tallyWords } from "./maplayout.js";
import { isExpanded, memberWords, todayWords } from "./mapstage.js";
import { Row, Expanded } from "./mapidea.js";
import { MapFoot, seedRaised, useRaise } from "./mapfoot.js";

const listed = (key) => mapUi.value[key] || [];
const toggle = (key, id) => {
  const list = listed(key);
  mapUi.value = { ...mapUi.value, [key]: list.includes(id) ? list.filter((x) => x !== id) : [...list, id] };
};

/** The goal shown: the one the Board shows if the Map has it, else the one kept for this project, else the first. */
export function shownGoal(m) {
  const goals = m.goals || [];
  return goals.find((g) => g.slug === track.value) || goals.find((g) => g.slug === keptGoal()) || goals[0] || null;
}

/** The whole party on one line, each member with its state in words; the alert only on one the work stopped on (spec 48 §3.2, §6). */
function Party({ g }) {
  if (!(g.party || []).length) return null;
  return html`<ul class="map-party" aria-label="Party">${g.party.map((m) => html`<li key=${m.slug}>
    <button type="button" class=${cls("map-party__member", { "is-needs": m.state === "needs", "is-work": m.state === "work" })} data-agent=${m.slug} data-state=${m.state}
      title=${`${m.name} · ${memberWords(m)}`} onClick=${() => openDialog("agent", { slug: m.slug })}>
      <${WhoHead} head=${m.head} small /><span>${m.name}</span> <span class="map-party__state">${memberWords(m)}${m.state === "work" ? " ↻" : ""}</span></button></li>`)}</ul>`;
}

/** The goal: title and the picker, priority, state, the flag, how far it is, what it did and cost, the branch results land in. */
function Header({ m, g, nodes }) {
  const flagRef = useRef();
  const raising = useRaise(g, flagRef);
  const more = listed("more").includes(g.slug), lines = g.done_when || [];
  const pct = progressOf(nodes), done = nodes.filter((n) => n.state === "done").length;
  const into = review.value?.into;
  const pick = (slug) => { track.value = slug; keepGoal(slug); };
  const flag = g.verdict ? (g.verdict.met ? "is-met" : "is-not") : "";
  const cost = [spentWords(g.usd), todayWords(g.today)].filter(Boolean).join(" · ");
  return html`<header class="map-goal__head">
    <div class="map-goal__line">
      <h3 class="map-goal__title">${g.title}</h3>
      ${m.goals.length > 1 && html`<select class="ork-field map-goal__pick" aria-label="Show another goal" value=${g.slug} onChange=${(e) => pick(e.target.value)}>
        ${m.goals.map((x) => html`<option key=${x.slug} value=${x.slug}>${x.short || x.title}</option>`)}</select>`}
      <span class="board-prio" data-priority=${g.priority}>${PRIORITY_WORDS[g.priority] || "Normal"}</span>
      <span class="map-goal__state ok-tone-muted">${goalState(g.state)}</span>
      ${g.verdict && html`<span class=${cls("trail-end map-goal__flag", flag)} ref=${flagRef} aria-label=${g.verdict.met ? `The flag: accepted by ${g.verdict.by}` : `The flag: not met, says ${g.verdict.by}`}>
        <span class=${cls("trail-end__flag", { "is-raising": raising })}><${Icon} name="flag" /></span>
        <span class="ok-font-status">${g.verdict.met ? `accepted by ${g.verdict.by}` : `not met, says ${g.verdict.by}`}</span>
        ${g.verdict.met && g.verdict.tally && html`<span class="trail-end__tally ok-font-status ok-tone-muted">${tallyWords(g.verdict.tally)}</span>`}</span>`}
      ${into && html`<button type="button" class="ork-btn map-goal__into" aria-haspopup="dialog" onClick=${() => openDialog("into")}>Merge into <b>${into}</b><${Chev} /></button>`}
    </div>
    <div class="map-goal__line map-goal__progress">
      <span class="ork-meter" aria-hidden="true">${Array.from({ length: 10 }, (_, i) => html`<i key=${i} class=${i < Math.round(pct / 10) ? "on" : ""}></i>`)}</span>
      <b class="map-goal__count" aria-label=${`${pct} % of the way`}>${pct} %</b>
      <span class="ok-font-status ok-tone-muted">${done} of ${nodes.length} ideas done</span>
      ${cost && html`<span class="map-goal__usd ok-font-status ok-tone-muted">${cost}</span>`}
    </div>
    ${lines.length > 0 && html`<p class="map-goal__when ok-font-status ok-tone-muted">done when ${lines[0].replace(/^done when /i, "")}${lines.length > 1 && !more ? html` <button class="board-link" onClick=${() => toggle("more", g.slug)}>and ${lines.length - 1} more</button>` : ""}
      ${more ? lines.slice(1).map((l) => html`<br />done when ${l.replace(/^done when /i, "")}`) : ""}</p>`}
    <${Party} g=${g} />
  </header>`;
}

/** One goal: its header, its ideas in trail order, Done (n). */
function Goal({ m, g }) {
  const nodes = m.nodes.filter((n) => n.goal === g.slug), since = mapSince.value;
  const titles = Object.fromEntries(m.nodes.map((n) => [n.slug, n.title]));
  const [folded, setFolded] = useState([]);                 // expanded ideas the person folded; collapsed ones the person opened
  const open = (n) => (folded.includes(n.slug) ? !isExpanded(n) : isExpanded(n));
  const flip = (slug) => setFolded(folded.includes(slug) ? folded.filter((x) => x !== slug) : [...folded, slug]);
  const done = nodes.filter((n) => n.state === "done"), rest = nodes.filter((n) => n.state !== "done");
  const doneOpen = listed("done").includes(g.slug);
  return html`<section class="map-goal" aria-label=${g.title} data-goal=${g.slug}>
    <${Header} m=${m} g=${g} nodes=${nodes} />
    <ul class="map-ideas" aria-label=${`Ideas of ${g.title}`}>
      ${rest.map((n) => open(n) ? html`<${Expanded} key=${n.slug} n=${n} goal=${g} titles=${titles} onFold=${() => flip(n.slug)} />`
        : html`<${Row} key=${n.slug} n=${n} titles=${titles} since=${since} goal=${g} onOpen=${flip} />`)}
    </ul>
    ${!rest.length && !done.length && html`<p class="trail-empty ok-tone-muted">No ideas yet</p>`}
    ${done.length > 0 && html`<div class="map-done">
      <button class="board-link map-done__btn" aria-expanded=${doneOpen} onClick=${() => toggle("done", g.slug)}>Done (${done.length})</button>
      ${doneOpen && html`<ul class="map-ideas map-done__list" aria-label=${`Done in ${g.title}`}>${done.map((n) => html`<${Row} key=${n.slug} n=${n} titles=${titles} since=${since} goal=${g} done />`)}</ul>`}
    </div>`}
  </section>`;
}

export function MapView() {
  const m = mapData.value;
  const el = useRef();
  useLayoutEffect(() => { if (el.current) el.current.scrollTop = mapView.top; }, []);       // the Map keeps its scroll when its tab comes back
  if (!m) return html`<p class="ok-tone-muted map-note">Reading the Map…</p>`;
  seedRaised(m);
  const g = shownGoal(m);
  return html`<div class="map" ref=${el} aria-label="Map" onScroll=${(e) => { mapView.top = e.currentTarget.scrollTop; }}>
    <${Cards} />
    ${!g ? html`<div class="shell-empty"><p>No goals yet</p><p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New goal</button></p></div>`
      : html`<${Goal} key=${g.slug} m=${m} g=${g} />`}
    <${MapFoot} m=${m} />
  </div>`;
}
