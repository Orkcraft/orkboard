// The check (docs/specs/38-operations.md §10.3): a prepared operation before its action. What was found (read-only), the doubts as
// lines with a warning, the draft parts and the fields with an `at` editable in place; a field without one is editable too, but
// its change needs Prepare again, and the action's button becomes that. A failed operation opens here too: its line and what
// can be done.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { runOf, templateOf, useOps } from "../board/store.js";
import { run, firstPart } from "../board/ops.js";
import { Field } from "./opdialog.js";
import { Modal, closeDialog } from "./modals.js";

const WAITING = { preparing: "It is being prepared…", acting: "It is being done…", held: "It waits for the limits…", done: "It is done.", dropped: "It was dropped." };

export function OpCheckDialog({ op }) {
  useOps();
  const r = runOf(op), t = r && templateOf(r.template);
  const [fields, setFields] = useState({});         // only what the person changed
  const [draft, setDraft] = useState({});
  const [busy, setBusy] = useState(false);
  if (!r || !t) return html`<${Modal} title="Operation" onClose=${closeDialog}><p class="ok-tone-muted">This operation is gone.</p><//>`;
  const go = async (name, args, close = true) => {
    setBusy(true);
    const got = await run(name, { id: r.id, ...args });
    setBusy(false);
    if (got && close) closeDialog();
  };
  if (r.state === "failed") {
    return html`<${Modal} title=${`Failed: ${t.title}`} onClose=${closeDialog}
      foot=${html`<button type="button" class="ok-btn" disabled=${busy} onClick=${() => go("ops.drop", {})}>Drop</button>
        <button type="button" class="ok-btn" disabled=${busy} title="Adds a new operation with the same form" onClick=${() => go("ops.again", {})}>Add again</button>
        ${r.acted === false && html`<button type="button" class="ok-btn primary" disabled=${busy} onClick=${() => go("ops.retry", {})}>Try again</button>`}`}>
      <div class="shell-form" data-op=${r.id}>
        <p class="ok-tone-error" role="alert">${r.why || "It failed"}</p>
        ${r.acted !== false && html`<p class="ok-font-status ok-tone-muted">It may have been done: look in the tool before you add it again.</p>`}
      </div>
    <//>`;
  }
  if (r.state !== "check") {
    return html`<${Modal} title=${t.title} onClose=${closeDialog}><p class="ok-tone-muted" data-op=${r.id}>${WAITING[r.state] || r.state}</p><//>`;
  }
  const value = (f) => fields[f.name] ?? r.fields[f.name] ?? "";
  const part = (p) => draft[p.name] ?? r.draft[p.name] ?? "";
  const changed = t.fields.filter((f) => f.name in fields && fields[f.name] !== (r.fields[f.name] ?? ""));
  const again = changed.some((f) => !f.at);
  const sent = () => ({
    fields: Object.fromEntries(changed.map((f) => [f.name, fields[f.name]])),
    draft: Object.fromEntries(t.draft.filter((p) => p.name in draft && draft[p.name] !== (r.draft[p.name] ?? "")).map((p) => [p.name, draft[p.name]])),
  });
  const hasAt = t.fields.filter((f) => f.at), noAt = t.fields.filter((f) => !f.at);
  return html`<${Modal} title=${t.title} onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ok-btn danger" disabled=${busy} title="Throws it away: nothing is done" onClick=${() => go("ops.drop", {})}>Drop</button>
      <button type="button" class="ok-btn primary" data-act=${again ? "prepare" : "act"} disabled=${busy}
        title=${again ? "Prepares it again with the form as changed; nothing is done yet" : `${t.act_label}: this is done at once`}
        onClick=${() => go(again ? "ops.prepare" : "ops.act", sent())}>${again ? "Prepare again" : t.act_label}</button>`}>
    <div class="shell-form board-check" data-op=${r.id}>
      ${r.why && html`<p class="ok-font-status ok-tone-muted" data-check="why">${r.why}</p>`}
      ${r.doubts.length > 0 && html`<ul class="board-doubts" aria-label="Doubts">${r.doubts.map((d, n) => html`<li key=${n}><span aria-hidden="true">⚠</span> ${d}</li>`)}</ul>`}
      ${r.found.length > 0 && html`<div class="shell-field" role="group" aria-label="What was found"><span class="ok-font-label">What was found</span>
        <dl class="board-found">${r.found.map((x, n) => html`<div key=${n}><dt>${x.label}</dt><dd>${x.value}</dd></div>`)}</dl></div>`}
      ${t.draft.map((p) => html`<${Field} key=${p.name} f=${p} value=${part(p)} onInput=${(v) => setDraft({ ...draft, [p.name]: v })} />`)}
      ${hasAt.map((f) => html`<${Field} key=${f.name} f=${f} value=${value(f)} onInput=${(v) => setFields({ ...fields, [f.name]: v })} />`)}
      ${noAt.length > 0 && html`<div class="shell-field" role="group" aria-label="The form"><span class="ok-font-label">The form</span>
        <span class="ok-font-status ok-tone-muted">Changing one of these prepares it again.</span>
        ${noAt.map((f) => html`<${Field} key=${f.name} f=${f} value=${value(f)} onInput=${(v) => setFields({ ...fields, [f.name]: v })} />`)}</div>`}
    </div>
  <//>`;
}
