// The goal select and the ideas (docs/specs/35-goals-window.md §11.1, §11.3): a select of the goals with New goal and the Target
// chip; a chosen goal shows its Summary's first line, Open and Edit, and filters Needs you and the ideas. Ideas are one row each —
// title, priority mark, state in words, actions; they drag to reorder, and a click opens the idea's spec in the preview.
import { useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { say, town } from "../link.js";
import { board, track, stateWords, goalList, hhmm, PRIORITY_WORDS, OPS } from "./store.js";
import { act as run, preview, showIdea, showGoal } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { TargetChip } from "./target.js";
import { NewMenu } from "./ops.js";

const DRAG = "text/x-board-slug";
const drag = (slug) => (e) => { e.dataTransfer.setData(DRAG, slug); e.dataTransfer.effectAllowed = "move"; };
const takes = (e) => e.dataTransfer.types.includes(DRAG);

const GOAL_WORDS = { reading: "reading", asks: "asks you", ready: "ready" };
const firstLine = (text) => String(text || "").split("\n").map((l) => l.trim()).find(Boolean) || "";

export function Goals() {
  const goals = goalList();
  const g = goals.find((x) => x.slug === track.value);
  const inOps = track.value === OPS;
  return html`<div class="board-goals" aria-label="Goals">
    <div class="board-row board-goals__bar">
      <select class="ork-field board-goals__select" aria-label="Goal" value=${track.value} onChange=${(e) => { track.value = e.target.value; }}>
        <option value="">All goals</option>
        ${goals.map((x) => html`<option key=${x.slug} value=${x.slug}>${x.title} · ${PRIORITY_WORDS[x.priority] || "Normal"}${GOAL_WORDS[x.state] ? ` · ${say(GOAL_WORDS[x.state])}` : ""}</option>`)}
        ${town.value?.ops_rev !== undefined && html`<option disabled>──────────</option><option value=${OPS}>Operations</option>`}</select>
      <button class="ork-btn" onClick=${() => openDialog("goal")}>New goal</button>
      ${inOps ? html`<${NewMenu} />` : html`<${TargetChip} />`}</div>
    ${g && html`<div class="board-goals__one" data-state=${g.state}>
      <p class="board-goals__line">${firstLine(g.summary) || html`<span class="ok-tone-muted">${g.state === "reading" ? "Reading the goal…" : "No summary yet."}</span>`}</p>
      <div class="board-row"><button class="ork-btn" aria-label=${`Open goal ${g.title}`} onClick=${() => showGoal(g.slug, { via: "board" })}>Open</button>
        <button class="ork-btn" aria-label=${`Edit goal ${g.title}`} onClick=${() => openDialog("goal", { slug: g.slug })}>Edit</button></div></div>`}
  </div>`;
}

/** What an idea's row says (§11.3) and the actions it has: [words, spinner, actions]. */
export function rowOf(i, titles) {
  const waits = (i.waits_on || []).map((s) => titles[s] || s);
  const limits = i.held_until ? `waits for limits · after ${hhmm(i.held_until)}` : "";
  if ((i.state === "raw" || i.state === "ready") && limits) return [limits, false, ["delete"]];
  if (i.state === "raw") {
    if (i.queue === "hold") return ["stopped", false, ["now", "tonight", "delete"]];
    if (i.queue === "now") return ["drafting", true, ["stop"]];
    return ["tonight", false, ["now", "delete"]];
  }
  if (i.state === "reading") return ["drafting", true, ["stop"]];
  if (i.state === "planning") return ["planning", true, ["stop"]];
  if (i.state === "plan" && i.start_at === "night") return ["starts tonight", false, ["start_now"]];
  if (i.state === "working") return [`${stateWords(i)}${waits.length ? ` · waits for ${waits.join(", ")}` : ""}`, false, ["halt"]];
  return [stateWords(i), false, []];
}

function Card({ i, titles }) {
  const [over, setOver] = useState(false);
  const [sure, setSure] = useState(false);
  const [words, spin, acts] = rowOf(i, titles);
  const t = i.title;
  const go = {
    now: () => run("ideas.queue", { slug: i.slug, queue: "now" }),
    tonight: () => run("ideas.queue", { slug: i.slug, queue: "night" }),
    stop: () => run("ideas.read_stop", { slug: i.slug }),
    start_now: () => run("ideas.start_now", { slug: i.slug }),
    halt: () => run("ideas.stop", { slug: i.slug }),
    drop: () => run("ideas.drop", { slug: i.slug }),
  };
  return html`<li class="board-card-row" data-queue=${i.queue || ""}><button draggable="true" onDragStart=${drag(i.slug)} data-state=${i.state}
    class=${cls("board-card kit-well", { "is-on": preview.value?.slug === i.slug && preview.value?.kind === "idea", "is-over": over })}
    onDragOver=${(e) => { if (takes(e)) { e.preventDefault(); setOver(true); } }} onDragLeave=${() => setOver(false)}
    onDrop=${(e) => { e.preventDefault(); setOver(false); const s = e.dataTransfer.getData(DRAG);
      if (s && s !== i.slug) run("ideas.move", { slug: s, track: i.track, before: i.slug }); }}
    onClick=${() => showIdea(i.slug, { via: "board" })}>
    <b class="board-card__title">${t}</b>
    <span class="board-card__meta">${i.size && html`<span class="board-size kit-well">${i.size}</span>`}
      <span class="board-prio" data-priority=${i.priority}>${PRIORITY_WORDS[i.priority] || "Normal"}</span>
      <span class="board-state" data-state=${i.state}>${spin && html`<span class="shell-spin" aria-hidden="true">↻</span> `}${words}</span></span>
  </button>
  <div class="board-card__acts">
    ${acts.includes("now") && html`<button class="ork-btn board-card__now" aria-label=${`Process now: ${t}`} title=${say("The Taskmaster drafts it at once")} onClick=${go.now}>Process now</button>`}
    ${acts.includes("tonight") && html`<button class="ork-btn" aria-label=${`Tonight: ${t}`} onClick=${go.tonight}>Tonight</button>`}
    ${acts.includes("stop") && html`<button class="ork-btn danger" aria-label=${`Stop: ${t}`} onClick=${go.stop}>Stop</button>`}
    ${acts.includes("start_now") && html`<button class="ork-btn" aria-label=${`Start now: ${t}`} onClick=${go.start_now}>Start now</button>`}
    ${acts.includes("halt") && html`<button class="ork-btn danger" aria-label=${`Stop: ${t}`} onClick=${go.halt}>Stop</button>`}
    ${acts.includes("delete") && (sure ? html`<button class="ork-btn danger" aria-label=${`Delete it: ${t}`} onClick=${go.drop}>Delete it</button>
        <button class="ork-btn" onClick=${() => setSure(false)}>Keep it</button>`
      : html`<button class="ork-btn" aria-label=${`Delete: ${t}`} onClick=${() => setSure(true)}>Delete</button>`)}
  </div></li>`;
}

export function Ideas() {
  const b = board.value;
  const titles = Object.fromEntries(b.ideas.map((i) => [i.slug, i.title]));
  const mine = b.ideas.filter((i) => (!track.value || i.track === track.value) && !i.in_needs_you && i.state !== "proposed")
    .sort((x, y) => x.order - y.order);
  const open_ = mine.filter((i) => i.state !== "done"), done = mine.filter((i) => i.state === "done");
  const some = (b.tracks || []).some((g) => g.slug !== "general");
  return html`<section class="board-ideas" aria-label="Ideas">
    <h3 class="board-sub kit-band">Ideas ${open_.length ? html`<span class="board-count kit-well">${open_.length}</span>` : ""}
      <button class="ork-btn primary board-ideas__new" onClick=${() => (some ? openDialog("idea", track.value ? { goal: track.value } : {}) : openDialog("goal", { then: "idea" }))}>New idea</button></h3>
    ${open_.length ? html`<ul class="board-list">${open_.map((i) => html`<${Card} key=${i.slug} i=${i} titles=${titles} />`)}</ul>`
      : html`<p class="ok-tone-muted">No idea here yet.</p>`}
    ${done.length > 0 && html`<details class="board-done"><summary>Done (${done.length})</summary>
      <ul class="board-list">${done.map((i) => html`<${Card} key=${i.slug} i=${i} titles=${titles} />`)}</ul></details>`}
  </section>`;
}
