// One round of questions (docs/specs/35-goals-window.md §0, §11.2): a box per question, answered together, one Send. The
// keeper asks at most three, all at once, and asks nothing more after the answers.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";

export function Questions({ questions, onSend, busy = false }) {
  const [answers, setAnswers] = useState(() => questions.map(() => ""));
  const [sending, setSending] = useState(false);
  const send = async (e) => {
    e?.preventDefault();
    if (sending) return;
    setSending(true);
    await onSend(questions.map((_, n) => (answers[n] || "").trim()));
    setSending(false);
  };
  return html`<form class="board-questions" id="board-questions" onSubmit=${send}>
    ${questions.map((q, n) => html`<label key=${n} class="shell-field"><span class="ok-font-label">${q}</span>
      <textarea class="ok-input" rows="2" autofocus=${n === 0} value=${answers[n] || ""} aria-label=${`Answer ${n + 1}: ${q}`}
        onInput=${(e) => setAnswers(answers.map((a, i) => (i === n ? e.target.value : a)))}
        onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) send(e); }}></textarea></label>`)}
    <div class="board-row"><button type="submit" class="ok-btn primary" disabled=${sending || busy}>Send</button>
      <span class="ok-font-status ok-tone-muted">${say("The Taskmaster reads all your answers at once and asks nothing more.")}</span></div>
  </form>`;
}
