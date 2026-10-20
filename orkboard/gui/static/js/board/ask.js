// One round of questions (docs/specs/35-goals-window.md §0, §11.2): a box per question, answered together, one Send. The
// keeper asks at most three, all at once, and asks nothing more after the answers.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { WhoHead } from "../orkui.js";

/** `initial`: the answers a box starts with (the recommended ones, spec 41 §9); `hints`: a line under each question (its why). */
export function Questions({ questions, onSend, busy = false, initial = [], hints = [], askers = [] }) {
  const [answers, setAnswers] = useState(() => questions.map((_, n) => initial[n] || ""));
  const [sending, setSending] = useState(false);
  const send = async (e) => {
    e?.preventDefault();
    if (sending) return;
    setSending(true);
    await onSend(questions.map((_, n) => (answers[n] || "").trim()));
    setSending(false);
  };
  return html`<form class="board-questions" id="board-questions" onSubmit=${send}>
    ${questions.map((q, n) => html`<label key=${n} class="shell-field">${askers[n] && html`<span class="board-quick__by"><${WhoHead} head=${askers[n].head} small /> <small class="ok-tone-muted">${askers[n].name} asks:</small></span>`}<span class="ok-font-label">${q}</span>
      <textarea class="ork-field" rows="2" autofocus=${n === 0} value=${answers[n] || ""} aria-label=${`Answer ${n + 1}: ${q}`}
        onInput=${(e) => setAnswers(answers.map((a, i) => (i === n ? e.target.value : a)))}
        onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(e); }}></textarea>
      ${hints[n] && html`<small class="ok-tone-muted">${hints[n]}</small>`}</label>`)}
    <div class="board-row"><button type="submit" class="ork-btn primary" disabled=${sending || busy}>Send</button>
      <span class="ok-font-status ok-tone-muted">${say("The Taskmaster reads all your answers at once and asks nothing more.")}</span></div>
  </form>`;
}
