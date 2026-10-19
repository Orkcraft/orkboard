// Agents, in the lower part of the centre as VS Code's terminal (docs/specs/33-v1-shell.md §6–§7, spec 34 §3, spec 36 §5):
// a monitor — a block per role: its name, model, today's spend and its week (what a result costs, how often it is right the
// first time), what it takes, its chips (needs you first), Edit — with + Add agent at the top. A chip opens its task.
import { html, cls } from "../html.js";
import { say } from "../link.js";
import { agents, agentsLayout, roles, setLayout, showIdea, showGoal, showTask } from "./store.js";
import { openDialog } from "./modals.js";
import { holdWords } from "../board/store.js";

const GRUNT = { running: ["working", "↻"], testing: ["testing", ""], review: ["at Review", ""], ready: ["queued", ""],
  held: ["held", "⏳"], failed: ["needs you", "⚠"] };

const ORDER = ["failed", "running", "testing", "ready", "held", "review"];     // needs you · working · testing · queued · held · at Review
const byState = (a, b) => (ORDER.indexOf(a.state) + 1 || 99) - (ORDER.indexOf(b.state) + 1 || 99);

export function gruntWords(c) {
  const [word, mark] = GRUNT[c.state] || [c.state, ""];
  if (c.state === "held") return holdWords(c.note, c.waits_title) || "held";
  if (c.state === "ready" && c.note) return "stopped";
  return mark ? `${word} ${mark}` : word;
}

const money = (n) => `≈$${n < 10 ? n.toFixed(2) : Math.round(n)}`;
const API_PRICES = "At API prices, not your bill";
const usd = (n) => (n ? `${money(n)} today` : "");
const modelWords = (r, models) => (models || []).find((m) => m.id === r.model)?.label || r.model || "By Target";

/** A role's week (spec 36 §2): what a result cost and how often it was merged the first time, once it has three merged. */
export function weekWords(role) {
  const w = role.week;
  if (!w) return "";
  if (role.role === "taskmaster") return w.finished > 0 ? `${w.first_time}/${w.finished} tasks the first time` : "";
  if (!(w.merged >= 3)) return "";
  const first = `${w.first_time}/${w.finished} the first time`;
  return w.usd_per_merged != null ? `${money(w.usd_per_merged)} a result · ${first}` : first;
}

function Head({ role, models }) {
  const week = weekWords(role);
  return html`<div class="shell-role__head">
    <h3 class="shell-role__name">${say(role.name)}</h3>
    <button class="board-link" aria-label=${`Edit ${say(role.name)}`} onClick=${() => openDialog("agent", { slug: role.role })}>Edit</button>
    <span class="ok-font-status ok-tone-muted shell-role__facts">${modelWords(role, models)}${role.role === "taskmaster" ? "" : ` · up to ${role.max_parallel}`}${role.spend_today ? html` · <span title=${API_PRICES}>${usd(role.spend_today)}</span>` : ""}${week ? html` · <span class="shell-role__week" title=${week.includes("≈") ? API_PRICES : ""}>${week}</span>` : ""}</span>
  </div>`;
}

function Taskmaster({ role, models }) {
  const c = role.chips || [];
  const say_ = (c0) => `${c0.state === "talking" ? "talking about" : c0.state} “${c0.title}”`;
  const open = (c0) => (c0.goal ? showGoal(c0.goal, { via: "agents" }) : showIdea(c0.idea, { via: "agents" }));
  const lead = c.find((x) => x.state !== "waiting");
  return html`<div class="shell-role" data-role="taskmaster">
    <${Head} role=${role} models=${models} />
    ${role.state === "waiting" && role.waits_on
      ? html`<button class="shell-chip is-wait" onClick=${() => showIdea(role.waits_on.idea, { via: "agents" })}>${role.waits_on.text}</button>`
      : lead ? html`<button class="shell-chip is-live" onClick=${() => open(lead)}><span class="shell-spin" aria-hidden="true">↻</span> ${say_(lead)}</button>`
        : html`<span class="ok-tone-muted">nothing to do</span>`}
    ${c.filter((x) => x !== lead && x.state !== "waiting").map((x) => html`<button key=${x.goal || x.idea} class="shell-chip" onClick=${() => open(x)}>${say_(x)}</button>`)}
  </div>`;
}

function Worker({ role, done, models }) {
  const chips = role.chips || [];
  const mine = done.filter((d) => (d.role || "grunt") === role.role);
  return html`<div class="shell-role" data-role=${role.role === "grunt" ? "grunt" : "agent"} data-slug=${role.role}>
    <${Head} role=${role} models=${models} />
    ${role.kinds?.length > 0 && html`<span class="ok-font-status ok-tone-muted shell-role__takes">Takes: ${role.kinds.join(", ")}</span>`}
    ${chips.length ? html`<ul class="shell-chips">${[...chips].sort(byState).map((c) => html`<li key=${c.idea + c.task}><button
        class=${cls("shell-chip", `is-${c.state}`)} data-state=${c.state} onClick=${() => showTask(c.idea, c.task, { via: "agents" })}>
        <span class="shell-chip__state">${gruntWords(c)}</span>${c.by === "auto" && html`<span class="shell-chip__tag">by itself</span>`}${c.night && html`<span class="shell-chip__tag">tonight</span>`}<b>${c.title}</b><small class="ok-tone-muted">${c.idea_title}</small></button></li>`)}</ul>`
      : html`<span class="ok-tone-muted">No task runs now.</span>`}
    ${mine.length > 0 && html`<details class="shell-done"><summary>Done today (${mine.length})</summary>
      <ul class="shell-chips">${mine.map((d) => html`<li key=${d.idea + d.task}><button class="shell-chip is-done"
        onClick=${() => showTask(d.idea, d.task, { via: "agents" })}>${d.title}</button></li>`)}</ul></details>`}
  </div>`;
}

export function AgentsPane() {
  const a = agents.value;
  const hidden = agentsLayout.value.hidden;
  const live = (a?.roles || []).filter((r) => r.role !== "taskmaster").flatMap((r) => r.chips || [])
    .filter((c) => c.state === "running" || c.state === "testing").length;
  const models = roles.value?.models;
  return html`<section class=${cls("shell-agents", { "is-hidden": hidden })} aria-label="Agents">
    <header class="shell-pane__head"><h2>Agents ${live > 0 && html`<span class="shell-count">${live}</span>`}</h2>
      ${!hidden && html`<button class="ok-btn primary" onClick=${() => openDialog("agent")}>+ Add agent</button>`}
      <button class="ok-btn" aria-expanded=${!hidden} aria-label=${hidden ? "Show Agents (Ctrl+J)" : "Hide Agents (Ctrl+J)"}
        title="Ctrl+J" onClick=${() => setLayout({ hidden: !hidden })}>${hidden ? "▴ show" : "▾ hide"}</button></header>
    ${!hidden && html`<div class="shell-agents__body">
      ${a ? a.roles.map((r) => r.role === "taskmaster" ? html`<${Taskmaster} key=${r.role} role=${r} models=${models} />`
        : html`<${Worker} key=${r.role} role=${r} done=${a.done_today || []} models=${models} />`) : html`<p class="ok-tone-muted">Opening…</p>`}
    </div>`}
  </section>`;
}
