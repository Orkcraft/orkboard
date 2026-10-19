// The Map (docs/specs/39-map.md §4): the preview's first tab. A section per goal; its ideas as a tree, tiers from top to bottom
// (an idea under the ideas it depends on, a line between them), each a card with its words, its tasks as pips and its marks.
// A view of `ideas.map`: it changes nothing, its one action is open. Words of a node's state are the Board row's (`rowOf`).
// A goal says its team (its agents' heads; the checkers' checks, realm/idea_checks.py), an idea how many of its checks passed,
// a task its tag.
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, WhoHead } from "../orkui.js";
import { track, PRIORITY_WORDS, OPS } from "./store.js";
import { mapData, mapSince, mapFolded, mapUi, mapView, preview, showIdea } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { TASK_STATE, nodeView, tiersOf, wavesOf, curve, spentWords, goalState } from "./maplayout.js";

const toggle = (key, id) => {
  const list = mapUi.value[key];
  mapUi.value = { ...mapUi.value, [key]: list.includes(id) ? list.filter((x) => x !== id) : [...list, id] };
};

const pipState = (s) => (s === "merged" ? "done" : s === "running" || s === "testing" ? "working" : "open");

/** "checks 1/2": how many of the checks that apply to an idea passed; the names and states in its title. */
function checksMark(checks) {
  const on = (checks || []).filter((c) => c.applies);
  if (!on.length) return null;
  const passed = on.filter((c) => c.state === "passed").length;
  const words = on.map((c) => `${c.name}: ${c.state === "passed" ? "passed" : TASK_STATE[c.state] || "to come"}`).join(" · ");
  return html`<span class=${cls("map-card__checks", { "is-passed": passed === on.length })} title=${words} aria-label=${`Checks: ${passed} of ${on.length} passed. ${words}`}>checks ${passed}/${on.length}</span>`;
}

/** A goal's team: its agents' heads, the checkers' marked, each one's name in words beside. */
/** The goal's party: its leader, then its builders and checkers (a checker says so). */
function Team({ team, leader }) {
  if (!(team || []).length && !leader) return null;
  const words = (team || []).map((t) => `${t.name}${t.every ? " (checks every idea)" : t.checks ? " (checks)" : ""}`).join(", ");
  const line = leader ? `Led by ${leader.name}${words ? ` · ${words}` : ""}` : `Team: ${words}`;
  return html`<p class="map-goal__team ok-font-status ok-tone-muted" aria-label=${line}>
    <span class="map-goal__heads">${[leader, ...(team || [])].filter(Boolean).map((t) => html`<${WhoHead} key=${t.slug} head=${t.head} small />`)}</span> ${line}</p>`;
}

function Node({ n, titles, since }) {
  const v = nodeView(n, titles);
  const open = mapUi.value.tasks.includes(n.slug);
  const fresh = !!since && n.updated > since;
  const whole = [n.title, v.needs ? `${v.needs}` : v.words, v.wait, n.by_itself ? "by itself" : "", v.cost].filter(Boolean).join(" · ");
  return html`<li class="map-node" data-slug=${n.slug}>
    <button class=${cls("map-card", { "is-needs": !!v.needs, "is-wait": !!v.wait, "is-done": n.state === "done", "is-on": preview.value?.kind === "idea" && preview.value.slug === n.slug })}
      data-slug=${n.slug} data-state=${n.state} data-needs=${n.needs_you || ""} title=${whole}
      onClick=${() => showIdea(n.slug, { via: "map" })}>
      <b class="map-card__title">${n.title}</b>
      <span class="map-card__words">
        ${v.needs && html`<span class="map-card__needs" aria-hidden="true">●</span> `}${v.spin && html`<span class="shell-spin" aria-hidden="true">↻</span> `}<span>${v.needs && !v.words.includes(v.needs) ? `${v.words} · ${v.needs}` : v.words}</span>${v.wait && html` <span class="map-card__wait">· ${v.wait}</span>`}
        ${fresh && html` <span class="map-card__new">new</span>`}</span>
      <span class="map-card__marks">${n.by_itself && html`<span>by itself</span>`}${v.cost && html`<span>${v.cost}</span>`}${checksMark(n.checks)}</span>
    </button>
    ${n.tasks.length > 0 && html`<button class="map-pips" aria-expanded=${open} aria-label=${`Tasks of ${n.title}`} onClick=${() => toggle("tasks", n.slug)}>
      ${n.tasks.map((t) => html`<i key=${t.id} class="map-pip" data-pip=${pipState(t.state)} aria-hidden="true"></i>`)}<span>Tasks</span></button>`}
    ${open && html`<div class="map-tasks" aria-label=${`Tasks of ${n.title}`}>${wavesOf(n.tasks).map((wave, i) => html`<div key=${i} class="map-wave" data-wave=${i + 1}>
      ${wave.map((t) => html`<p key=${t.id} class="map-task" data-state=${t.state}><${WhoHead} head=${t.head} small /><code>${t.id}</code> ${t.title} · ${t.tag ? `${t.tag} · ` : ""}${TASK_STATE[t.state] || t.state}</p>`)}</div>`)}</div>`}
  </li>`;
}

/** One goal's tree: tiers as rows, the lines drawn under the nodes once they are laid out. */
function Tree({ nodes, edges, titles, since }) {
  const root = useRef(), last = useRef("");
  const [lines, setLines] = useState([]);
  const measure = () => {
    const el = root.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const out = [];
    for (const e of edges) {
      const a = el.querySelector(`.map-card[data-slug="${CSS.escape(e.from)}"]`)?.getBoundingClientRect();
      const b = el.querySelector(`.map-card[data-slug="${CSS.escape(e.to)}"]`)?.getBoundingClientRect();
      if (a && b) out.push({ from: e.from, to: e.to, d: curve({ x: a.left - r.left + a.width / 2, y: a.bottom - r.top }, { x: b.left - r.left + b.width / 2, y: b.top - r.top }) });
    }
    const key = JSON.stringify(out);
    if (key !== last.current) { last.current = key; setLines(out); }
  };
  useLayoutEffect(measure);                                         // after every render: an unfolded node moves what is under it
  useEffect(() => {
    if (typeof ResizeObserver !== "function") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(root.current);
    return () => ro.disconnect();
  }, []);
  return html`<div class="map-scroll"><div class="map-tree" ref=${root}>
    <svg class="map-lines" aria-hidden="true">${lines.map((l) => html`<path key=${l.from + l.to} d=${l.d} data-from=${l.from} data-to=${l.to} />`)}</svg>
    ${tiersOf(nodes).map((tier, i) => html`<ul key=${i} class="map-tier" data-tier=${tier[0].tier}>${tier.map((n) => html`<${Node} key=${n.slug} n=${n} titles=${titles} since=${since} />`)}</ul>`)}
  </div></div>`;
}

function Goal({ g, nodes, edges, titles, since }) {
  const folded = mapFolded.value.includes(g.slug);
  const done = nodes.filter((n) => n.folded);
  const doneOpen = mapUi.value.done.includes(g.slug), more = mapUi.value.more.includes(g.slug);
  const lines = g.done_when || [];
  const fold = () => { mapFolded.value = folded ? mapFolded.value.filter((x) => x !== g.slug) : [...mapFolded.value, g.slug]; };
  return html`<section class="map-goal" aria-label=${g.title} data-goal=${g.slug} data-folded=${folded}>
    <header class="map-goal__head">
      <button class="map-fold" aria-expanded=${!folded} aria-label=${`${folded ? "Unfold" : "Fold"} ${g.title}`} onClick=${fold}><${Chev} dir=${folded ? "right" : "down"} /></button>
      <h3 class="map-goal__title">${g.title}</h3>
      <span class="board-prio" data-priority=${g.priority}>${PRIORITY_WORDS[g.priority] || "Normal"}</span>
      <span class="map-goal__state ok-tone-muted">${goalState(g.state)}</span>
      <span class="map-goal__count">${g.done} of ${g.ideas} done</span>
      <span class="map-goal__usd ok-tone-muted">${spentWords(g.usd)}</span>
      ${g.verdict && html`<span class=${`map-goal__verdict ${g.verdict.met ? "ok-tone-ok" : "ok-tone-error"}`}>${g.verdict.met ? `accepted by ${g.verdict.by}` : `not met, says ${g.verdict.by}`}</span>`}
    </header>
    ${!folded && html`<${Team} team=${g.team} leader=${g.leader} />${lines.length > 0 && html`<p class="map-goal__when ok-font-status ok-tone-muted">done when ${lines[0]}${lines.length > 1 && !more ? html` <button class="board-link" onClick=${() => toggle("more", g.slug)}>and ${lines.length - 1} more</button>` : ""}
      ${more ? lines.slice(1).map((l) => html`<br />done when ${l}`) : ""}</p>`}
      ${nodes.some((n) => !n.folded) ? html`<${Tree} nodes=${nodes} edges=${edges} titles=${titles} since=${since} />` : html`<p class="ok-tone-muted">No open idea in this goal.</p>`}
      ${done.length > 0 && html`<div class="map-done">
        <button class="board-link map-done__btn" aria-expanded=${doneOpen} onClick=${() => toggle("done", g.slug)}>Done (${done.length})</button>
        ${doneOpen && html`<ul class="map-done__list">${done.map((n) => html`<${Node} key=${n.slug} n=${n} titles=${titles} since=${since} />`)}</ul>`}</div>`}`}
  </section>`;
}

export function MapView() {
  const m = mapData.value, since = mapSince.value;
  const el = useRef();
  useLayoutEffect(() => { if (el.current) el.current.scrollTop = mapView.top; }, []);       // the Map keeps its scroll when its tab comes back
  if (!m) return html`<p class="ok-tone-muted map-note">Reading the Map…</p>`;
  const goals = m.goals.filter((g) => !track.value || track.value === OPS || g.slug === track.value);
  const titles = Object.fromEntries(m.nodes.map((n) => [n.slug, n.title]));
  const goalOf = Object.fromEntries(m.nodes.map((n) => [n.slug, n.goal]));
  return html`<div class="map" ref=${el} aria-label="Map" onScroll=${(e) => { mapView.top = e.currentTarget.scrollTop; }}>
    ${!m.goals.length ? html`<div class="shell-empty"><p>No goals yet</p><p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New goal</button></p></div>`
      : goals.map((g) => html`<${Goal} key=${g.slug} g=${g} nodes=${m.nodes.filter((n) => n.goal === g.slug)}
        edges=${m.edges.filter((e) => goalOf[e.to] === g.slug)} titles=${titles} since=${since} />`)}
  </div>`;
}
