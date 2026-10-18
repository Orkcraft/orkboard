// The Stages section (docs/specs/35-goals-window.md §4, §11.4): the board writes it from plan.json as waves of tasks
// (`1. k1 The table (S) ∥ k2 The form (M)`); here each task shows its live state beside it, from the plan, in words.
import { html } from "../html.js";
import { showTask } from "../shell/store.js";

const WORDS = { merged: "merged", running: "working", testing: "working", held: "held", failed: "failed", review: "at Review",
  waiting: "waiting", ready: "queued" };
const MARKS = { merged: "✓", running: "↻", testing: "↻", held: "⏳", failed: "!", review: "●", waiting: "…", ready: "…" };

/** The waves of a Stages text: [[{id, text}]] — one array per line, one entry per task. */
export function waves(text) {
  return String(text || "").split("\n").map((line) => line.trim()).filter(Boolean).map((line) => line.replace(/^\d+[.)]\s*/, "")
    .split("∥").map((part) => {
      const m = /^(k\d+)\b\s*(.*)$/.exec(part.trim());
      return m ? { id: m[1], text: m[2] } : { id: "", text: part.trim() };
    }));
}

export function Stages({ text, plan, slug }) {
  const lines = waves(text);
  if (!lines.length) return html`<p class="ok-tone-muted">No stages yet.</p>`;
  const by = Object.fromEntries((plan?.tasks || []).map((k) => [k.id, k]));
  return html`<ol class="board-stages">${lines.map((wave, n) => html`<li key=${n} class="board-stages__wave">
    ${wave.map((t) => { const k = by[t.id]; return html`<span key=${t.id || t.text} class="board-stages__task" data-task=${t.id} data-state=${k?.state || ""}>
      ${t.id && html`<button class="board-link" onClick=${() => showTask(slug, t.id)}>${t.id}</button>`} <span>${t.text}</span>
      ${k && html`<span class="board-stages__state board-task__state" data-state=${k.state}><span aria-hidden="true">${MARKS[k.state] || ""}</span> ${WORDS[k.state] || k.state}</span>`}</span>`; })}
  </li>`)}</ol>`;
}
