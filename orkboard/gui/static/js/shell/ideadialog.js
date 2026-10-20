// New idea (docs/specs/35-goals-window.md §3): the text, the goal (required: the one chosen on the Board, else the first by
// priority; General is not listed), the lens of the goal's party (lens.js: what the idea points at, beside its text) and the
// priority (default the goal's). One button: Add. Closing the dialog with text in it adds it to tonight's queue (never lost);
// closing it empty adds nothing.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { goalList, track, PRIORITY_WORDS } from "../board/store.js";
import { act } from "./store.js";
import { Modal, closeDialog } from "./modals.js";
import { Lens, lensValue, noLens, useLenses } from "./lens.js";

export function IdeaDialog({ goal: first = "" }) {
  const goals = goalList();
  const [text, setText] = useState("");
  const [goal, setGoal] = useState(first || (goals.some((g) => g.slug === track.value) ? track.value : goals[0]?.slug) || "");
  const [mine, setMine] = useState("");                      // the person's own priority; "" = the goal's
  const [busy, setBusy] = useState(false);
  const [lens, setLens] = useState(noLens);
  const info = useLenses(goal);
  const priority = mine || goals.find((g) => g.slug === goal)?.priority || "normal";
  const send = async () => {
    const t = text.trim();
    if (!t || !goal || busy) return;
    setBusy(true);
    const pointed = lensValue(info, lens);
    const got = await act("ideas.add", { text: t, track: goal, priority, ...(pointed.length ? { lens: pointed } : {}) });
    setBusy(false);
    if (got?.slug) closeDialog();
  };
  const close = async () => {                 // closed with text in it: tonight's queue
    const t = text.trim();
    closeDialog();
    const pointed = lensValue(info, lens);
    if (t && goal) await act("ideas.add", { text: t, track: goal, priority, night: true, ...(pointed.length ? { lens: pointed } : {}) });
  };
  return html`<${Modal} title="New idea" onClose=${close} wide=${(info?.lenses || []).length > 1}
    foot=${html`<button type="button" class="ork-btn primary" disabled=${!text.trim() || !goal || busy} onClick=${send}
      title=${say("Add it: the Taskmaster drafts it at once, or tonight when its priority is Low")}>Add</button>`}>
    <div class="shell-form">
      <label class="shell-field"><span class="ok-font-label">Your idea</span>
        <textarea class="ork-field" rows="4" autofocus value=${text} aria-label="Your idea" placeholder="Your idea, in a few words or a few lines"
          onInput=${(e) => setText(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } }}></textarea></label>
      <label class="shell-field"><span class="ok-font-label">Belongs to goal</span>
        <select class="ork-field" aria-label="Goal" value=${goal} onChange=${(e) => { setGoal(e.target.value); setMine(""); }}>
          ${goals.map((g) => html`<option key=${g.slug} value=${g.slug}>${g.title}</option>`)}</select></label>
      <${Lens} info=${info} s=${lens} set=${setLens} />
      <label class="shell-field"><span class="ok-font-label">Priority</span>
        <select class="ork-field" aria-label="Priority" value=${priority} onChange=${(e) => setMine(e.target.value)}>
          ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>
      <p class="ok-font-status ok-tone-muted">${say("High and Normal: the Taskmaster drafts it at once. Low: tonight. Closing this with text in it adds it to tonight's queue.")}</p>
    </div>
  <//>`;
}
