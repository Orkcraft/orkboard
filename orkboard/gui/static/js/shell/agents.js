// Agents, in the lower part of the centre as VS Code's terminal (docs/specs/33-v1-shell.md §6–§7, spec 34 §3, spec 36 §5):
// a monitor — a block per role, one line (spec 41 §8): its head (its craft's race in its tier's gear, decisions §53), its name,
// ×2 (at most at once) and ≈ $0.40 a task (the Taskmaster's cost is its steps: it says its week), what it takes, its chips (needs you
// first, each with the head of who does it and its short name), Edit — with + Add agent at the top (from the library, or your own). A
// chip opens its task.
import { html, cls } from "../html.js";
import { Chev } from "../orkui.js";
import { say } from "../link.js";
import { agents, agentsLayout, setLayout, showIdea, showGoal, showTask } from "./store.js";
import { openDialog } from "./modals.js";
import { holdWords } from "../board/store.js";
import { WhoHead, CRAFT_WORDS, TIER_WORDS, RACE_WORDS } from "../orkui.js";

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

const API_PRICES = "At API prices, not your bill";
const AN = (race) => (/^[aeiou]/.test(RACE_WORDS[race]) ? "an" : "a");

/** The Taskmaster's week (spec 36 §2): how often a task is merged the first time, once there are enough to say. */
export function weekWords(role) {
  const w = role.week;
  return role.role === "taskmaster" && w && w.finished > 0 ? `${w.first_time}/${w.finished} tasks the first time` : "";
}

/** A role's words for a screen reader: "Docs scribe: an elf, Design, Seasoned; up to 2 at once; about $0.40 a task". */
export function roleWords(role) {
  const hd = role.head, usd = role.usd_task == null ? "" : `about $${Number(role.usd_task).toFixed(2)} a task`;
  const who = [hd ? `${AN(hd.race)} ${RACE_WORDS[hd.race]}` : "", CRAFT_WORDS[hd?.craft], TIER_WORDS[hd?.tier]].filter(Boolean).join(", ");
  return [`${role.name}${who ? `: ${who}` : ""}`, role.role === "taskmaster" ? "" : `up to ${role.max_parallel} at once`, usd, weekWords(role)].filter(Boolean).join("; ");
}

function Head({ role }) {
  const week = weekWords(role), tm = role.role === "taskmaster";
  return html`<div class="shell-role__head" role="group" aria-label=${roleWords(role)}>
    <${WhoHead} head=${role.head} />
    <h3 class="shell-role__name">${say(role.name)}</h3>
    ${!tm && html`<span class="shell-role__many" title=${`Up to ${role.max_parallel} at once`}>×${role.max_parallel}</span>`}
    ${role.usd_task != null && html`<span class="shell-role__usd" title=${API_PRICES}>≈ $${Number(role.usd_task).toFixed(2)} a task</span>`}
    <button class="board-link" aria-label=${`Edit ${say(role.name)}`} onClick=${() => openDialog("agent", { slug: role.role })}>Edit</button>
    ${week && html`<span class="ok-font-status ok-tone-muted shell-role__facts"><span class="shell-role__week">${week}</span></span>`}
  </div>`;
}

function Taskmaster({ role }) {
  const c = role.chips || [];
  const say_ = (c0) => `${c0.state === "talking" ? "talking about" : c0.state} “${c0.short || c0.title}”`;
  const open = (c0) => (c0.goal ? showGoal(c0.goal, { via: "agents" }) : showIdea(c0.idea, { via: "agents" }));
  const lead = c.find((x) => x.state !== "waiting");
  return html`<div class="shell-role" data-role="taskmaster">
    <${Head} role=${role} />
    ${role.state === "waiting" && role.waits_on
      ? html`<button class="shell-chip is-wait" onClick=${() => showIdea(role.waits_on.idea, { via: "agents" })}>${role.waits_on.text}</button>`
      : lead ? html`<button class="shell-chip is-live" onClick=${() => open(lead)}><span class="shell-spin" aria-hidden="true">↻</span> ${say_(lead)}</button>`
        : html`<span class="ok-tone-muted">nothing to do</span>`}
    ${c.filter((x) => x !== lead && x.state !== "waiting").map((x) => html`<button key=${x.goal || x.idea} class="shell-chip" onClick=${() => open(x)}>${say_(x)}</button>`)}
  </div>`;
}

function Worker({ role, done }) {
  const chips = role.chips || [];
  const mine = done.filter((d) => (d.role || "grunt") === role.role);
  return html`<div class="shell-role" data-role=${role.role === "grunt" ? "grunt" : "agent"} data-slug=${role.role}>
    <${Head} role=${role} />
    ${role.kinds?.length > 0 && html`<span class="ok-font-status ok-tone-muted shell-role__takes">Takes: ${role.kinds.join(", ")}</span>`}
    ${chips.length ? html`<ul class="shell-chips">${[...chips].sort(byState).map((c) => html`<li key=${c.idea + c.task}><button
        class=${cls("shell-chip", `is-${c.state}`)} data-state=${c.state} title=${c.title} aria-label=${`${c.title}: ${gruntWords(c)}`} onClick=${() => showTask(c.idea, c.task, { via: "agents" })}>
        <${WhoHead} head=${c.head} small /><span class="shell-chip__state">${gruntWords(c)}</span>${c.by === "auto" && html`<span class="shell-chip__tag">by itself</span>`}${c.night && html`<span class="shell-chip__tag">tonight</span>`}<b class="shell-chip__name">${c.short || c.title}</b><small class="ok-tone-muted shell-chip__idea">${c.idea_short || c.idea_title}</small></button></li>`)}</ul>`
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
  return html`<section class=${cls("shell-agents", { "is-hidden": hidden })} aria-label="Agents">
    <header class="shell-pane__head"><h2>Agents ${live > 0 && html`<span class="shell-count">${live}</span>`}</h2>
      ${!hidden && html`<button class="ork-btn primary" onClick=${() => openDialog("agent")}>+ Add agent</button>`}
      <button class="ork-btn" aria-expanded=${!hidden} aria-label=${hidden ? "Show Agents (Ctrl+J)" : "Hide Agents (Ctrl+J)"}
        title="Ctrl+J" onClick=${() => setLayout({ hidden: !hidden })}>${hidden ? html`<${Chev} dir="up" /> show` : html`<${Chev} /> hide`}</button></header>
    ${!hidden && html`<div class="shell-agents__body">
      ${a ? a.roles.map((r) => r.role === "taskmaster" ? html`<${Taskmaster} key=${r.role} role=${r} />`
        : html`<${Worker} key=${r.role} role=${r} done=${a.done_today || []} />`) : html`<p class="ok-tone-muted">Opening…</p>`}
    </div>`}
  </section>`;
}
