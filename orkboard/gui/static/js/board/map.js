// The Map (docs/specs/39-map.md §4, decisions §53): the preview's first tab, a trail for each goal, one under the other. A trail
// runs from how far the goal is (in %, at its start) through the ideas left to do — stops, from left to right, an idea right of
// the ideas it depends on, the ones that can go at once side by side (three at most, the rest a click away) — to the goal's flag,
// raised when its leader accepts it against its metrics (the verdict). An idea at work shows its tasks left, each with the head
// of the agent who does it, in the waves they go in; what is done is not on the trail (a click shows it). A stop that waits for
// the person is a gate on the trail. A view of `ideas.map`: it changes nothing, its one action is open. Words of a stop's state
// are the Board row's (`rowOf`).
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Icon, WhoHead } from "../orkui.js";
import { PRIORITY_WORDS } from "./store.js";
import { mapData, mapSince, mapFolded, mapUi, mapView, preview, showIdea, showTask } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { TASK_STATE, nodeView, tiersOf, wavesOf, spentWords, goalState, progressOf, leftToDo, trailCurve, trailEdges } from "./maplayout.js";

const LANES = 3;                       // the stops side by side in one step of the trail, before "+N more"
const TASKS = 6;                       // the tasks left shown on a stop at work

const listed = (key) => mapUi.value[key] || [];
const toggle = (key, id) => {
  const list = listed(key);
  mapUi.value = { ...mapUi.value, [key]: list.includes(id) ? list.filter((x) => x !== id) : [...list, id] };
};

/** "checks 1/2": how many of the checks that apply to an idea passed; the names and states in its title. */
function checksMark(checks) {
  const on = (checks || []).filter((c) => c.applies);
  if (!on.length) return null;
  const passed = on.filter((c) => c.state === "passed").length;
  const words = on.map((c) => `${c.name}: ${c.state === "passed" ? "passed" : TASK_STATE[c.state] || "to come"}`).join(" · ");
  return html`<span class=${cls("map-card__checks", { "is-passed": passed === on.length })} title=${words} aria-label=${`Checks: ${passed} of ${on.length} passed. ${words}`}>checks ${passed}/${on.length}</span>`;
}

/** The goal's party: its leader, then its builders and checkers (a checker says so). */
function Team({ team, leader }) {
  if (!(team || []).length && !leader) return null;
  const words = (team || []).map((t) => `${t.name}${t.every ? " (checks every idea)" : t.checks ? " (checks)" : ""}`).join(", ");
  const line = leader ? `Led by ${leader.name}${words ? ` · ${words}` : ""}` : `Team: ${words}`;
  return html`<p class="map-goal__team ok-font-status ok-tone-muted" aria-label=${line}>
    <span class="map-goal__heads">${[leader, ...(team || [])].filter(Boolean).map((t) => html`<${WhoHead} key=${t.slug} head=${t.head} small />`)}</span> ${line}</p>`;
}

/** An idea not yet planned is in the fog: its tasks are not known yet. */
const fog = (n) => !n.tasks.length && ["raw", "reading", "asks", "ready", "planning", "proposed"].includes(n.state);

/** A stop: the idea's card, a gate above it when it waits for the person, its tasks left with their agents' heads. */
function Stop({ n, titles, since }) {
  const v = nodeView(n, titles);
  const fresh = !!since && n.updated > since;
  const left = n.tasks.filter(leftToDo), doneTasks = n.tasks.length - left.length;
  const whole = [n.title, v.needs ? `${v.needs}` : v.words, v.wait, n.by_itself ? "by itself" : "", v.cost].filter(Boolean).join(" · ");
  return html`<li class=${cls("map-node", { "is-gate": !!v.needs })} data-slug=${n.slug}>
    ${v.needs && html`<span class="trail-gate"><${Icon} name="warning-diamond" /> Waits for you</span>`}
    <button class=${cls("map-card", { "is-needs": !!v.needs, "is-wait": !!v.wait, "is-fog": fog(n), "is-done": n.state === "done", "is-on": preview.value?.kind === "idea" && preview.value.slug === n.slug })}
      data-slug=${n.slug} data-state=${n.state} data-needs=${n.needs_you || ""} title=${whole}
      onClick=${() => showIdea(n.slug, { via: "map" })}>
      <b class="map-card__title">${n.title}</b>
      <span class="map-card__words">
        ${v.needs && html`<span class="map-card__needs" aria-hidden="true">●</span> `}${v.spin && html`<span class="shell-spin" aria-hidden="true">↻</span> `}<span>${v.needs && !v.words.includes(v.needs) ? `${v.words} · ${v.needs}` : v.words}</span>${v.wait && html` <span class="map-card__wait">· ${v.wait}</span>`}
        ${fresh && html` <span class="map-card__new">new</span>`}</span>
      <span class="map-card__marks">${n.by_itself && html`<span>by itself</span>`}${v.cost && html`<span>${v.cost}</span>`}${checksMark(n.checks)}</span>
    </button>
    ${left.length > 0 && n.state !== "done" && html`<div class="map-tasks" aria-label=${`Tasks of ${n.title}`}>
      ${wavesOf(left).map((wave, i) => html`<div key=${i} class="map-wave" data-wave=${i + 1}>
        ${wave.slice(0, TASKS).map((t) => html`<button key=${t.id} type="button" class="map-task" data-state=${t.state} title=${`${t.id} ${t.title} · ${t.tag ? `${t.tag} · ` : ""}${TASK_STATE[t.state] || t.state}`}
          onClick=${() => showTask(n.slug, t.id, { via: "map" })}><${WhoHead} head=${t.head} small /><span class="map-task__title">${t.title}</span>
          <small>${TASK_STATE[t.state] || t.state}</small></button>`)}</div>`)}
      ${doneTasks > 0 && html`<small class="map-tasks__done ok-tone-muted">${doneTasks} done</small>`}</div>`}
  </li>`;
}

/** One goal's trail: the start (how far, the done ones), its steps of stops, the flag; the lines drawn once laid out. */
function Trail({ g, nodes, edges, titles, since }) {
  const root = useRef(), last = useRef("");
  const [lines, setLines] = useState([]);
  const open = nodes.filter((n) => n.state !== "done");
  const steps = tiersOf(open);
  const wide = listed("lanes").includes(g.slug);
  const shownSlugs = steps.flatMap((s) => (wide ? s : s.slice(0, LANES)).map((n) => n.slug));
  const ways = trailEdges(shownSlugs, edges);
  const measure = () => {
    const el = root.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const at = (slug, side) => {
      const box = (slug === "@start" ? el.querySelector(".trail-start__dot") : slug === "@end" ? el.querySelector(".trail-end__flag")
        : el.querySelector(`.map-card[data-slug="${CSS.escape(slug)}"]`))?.getBoundingClientRect();
      return box && { x: (side === "out" ? box.right : box.left) - r.left, y: box.top + box.height / 2 - r.top };
    };
    const out = [];
    for (const e of ways) {
      const a = at(e.from, "out"), b = at(e.to, "in");
      if (a && b) out.push({ from: e.from, to: e.to, d: trailCurve(a, b) });
    }
    const key = JSON.stringify(out);
    if (key !== last.current) { last.current = key; setLines(out); }
  };
  useLayoutEffect(measure);                                         // after every render: a stop's tasks move what is beside it
  useEffect(() => {
    if (typeof ResizeObserver !== "function") return undefined;
    const ro = new ResizeObserver(measure);
    ro.observe(root.current);
    return () => ro.disconnect();
  }, []);
  const pct = progressOf(nodes), done = nodes.filter((n) => n.state === "done");
  const doneOpen = listed("done").includes(g.slug);
  const flag = g.verdict ? (g.verdict.met ? "is-met" : "is-not") : "";
  const flagWords = g.verdict ? (g.verdict.met ? `Met · ${g.verdict.by}` : `Not met yet · ${g.verdict.by}`) : open.length ? "The goal" : "Its ideas are done";
  return html`<div class="map-scroll"><div class="trail" ref=${root}>
    <svg class="map-lines" aria-hidden="true">${lines.map((l) => html`<path key=${l.from + l.to} d=${l.d} data-from=${l.from} data-to=${l.to} />`)}</svg>
    <div class="trail-start">
      <span class="trail-start__dot" aria-hidden="true"></span>
      <b class="trail-start__pct" aria-label=${`${pct} % of the way`}>${pct} %</b>
      <span class="ok-font-status ok-tone-muted">${done.length} of ${nodes.length} ideas</span>
      ${done.length > 0 && html`<button class="board-link map-done__btn" aria-expanded=${doneOpen} onClick=${() => toggle("done", g.slug)}>Done (${done.length})</button>`}
    </div>
    ${steps.map((step, i) => {
      const shown = wide ? step : step.slice(0, LANES);
      return html`<ul key=${i} class="map-tier trail-step" data-tier=${step[0].tier}>
        ${shown.map((n) => html`<${Stop} key=${n.slug} n=${n} titles=${titles} since=${since} />`)}
        ${step.length > LANES && html`<li class="trail-more"><button class="board-link" aria-expanded=${wide} onClick=${() => toggle("lanes", g.slug)}>
          ${wide ? "Fewer side by side" : `+${step.length - LANES} more side by side`}</button></li>`}</ul>`;
    })}
    ${!steps.length && html`<p class="trail-empty ok-tone-muted">No idea left on the way.</p>`}
    <div class=${cls("trail-end", flag)} aria-label=${`The flag: ${flagWords}`}>
      <span class="trail-end__flag"><${Icon} name="flag" /></span>
      <span class="ok-font-status">${flagWords}</span>
    </div>
  </div>
  ${doneOpen && html`<ul class="map-done__list" aria-label=${`Done in ${g.title}`}>${done.map((n) => html`<${Stop} key=${n.slug} n=${n} titles=${titles} since=${since} />`)}</ul>`}
  </div>`;
}

function Goal({ g, nodes, edges, titles, since }) {
  const folded = mapFolded.value.includes(g.slug);
  const more = listed("more").includes(g.slug);
  const lines = g.done_when || [];
  const fold = () => { mapFolded.value = folded ? mapFolded.value.filter((x) => x !== g.slug) : [...mapFolded.value, g.slug]; };
  return html`<section class="map-goal" aria-label=${g.title} data-goal=${g.slug} data-folded=${folded}>
    <header class="map-goal__head">
      <button class="map-fold" aria-expanded=${!folded} aria-label=${`${folded ? "Unfold" : "Fold"} ${g.title}`} onClick=${fold}><${Chev} dir=${folded ? "right" : "down"} /></button>
      <h3 class="map-goal__title">${g.title}</h3>
      <span class="board-prio" data-priority=${g.priority}>${PRIORITY_WORDS[g.priority] || "Normal"}</span>
      <span class="map-goal__state ok-tone-muted">${goalState(g.state)}</span>
      <span class="map-goal__count">${progressOf(nodes)} %</span>
      <span class="map-goal__usd ok-tone-muted">${spentWords(g.usd)}</span>
      ${g.verdict && html`<span class=${`map-goal__verdict ${g.verdict.met ? "ok-tone-ok" : "ok-tone-error"}`}>${g.verdict.met ? `accepted by ${g.verdict.by}` : `not met, says ${g.verdict.by}`}</span>`}
    </header>
    ${!folded && html`<${Team} team=${g.team} leader=${g.leader} />${lines.length > 0 && html`<p class="map-goal__when ok-font-status ok-tone-muted">done when ${lines[0]}${lines.length > 1 && !more ? html` <button class="board-link" onClick=${() => toggle("more", g.slug)}>and ${lines.length - 1} more</button>` : ""}
      ${more ? lines.slice(1).map((l) => html`<br />done when ${l}`) : ""}</p>`}
      <${Trail} g=${g} nodes=${nodes} edges=${edges} titles=${titles} since=${since} />`}
  </section>`;
}

export function MapView() {
  const m = mapData.value, since = mapSince.value;
  const el = useRef();
  useLayoutEffect(() => { if (el.current) el.current.scrollTop = mapView.top; }, []);       // the Map keeps its scroll when its tab comes back
  if (!m) return html`<p class="ok-tone-muted map-note">Reading the Map…</p>`;
  const titles = Object.fromEntries(m.nodes.map((n) => [n.slug, n.title]));
  const goalOf = Object.fromEntries(m.nodes.map((n) => [n.slug, n.goal]));
  return html`<div class="map" ref=${el} aria-label="Map" onScroll=${(e) => { mapView.top = e.currentTarget.scrollTop; }}>
    ${!m.goals.length ? html`<div class="shell-empty"><p>No goals yet</p><p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New goal</button></p></div>`
      : m.goals.map((g) => html`<${Goal} key=${g.slug} g=${g} nodes=${m.nodes.filter((n) => n.goal === g.slug)}
        edges=${m.edges.filter((e) => goalOf[e.to] === g.slug)} titles=${titles} since=${since} />`)}
  </div>`;
}
