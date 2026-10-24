// The check (docs/specs/38-operations.md §10.3): a prepared operation before its action. What was found (read-only), the doubts as
// lines with a warning, the draft parts and the fields with an `at` editable in place; a field without one is editable too, but
// its change needs Prepare again, and the action's button becomes that. A failed operation opens here too: its line and what
// can be done. A brief (docs/specs/66-team-briefs.md §7) has no action: its draft is a page to correct, the last one it follows
// (Last time) read-only, and Keep, Prepare again, Drop; once kept it opens read-only, with Copy.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { runOf, templateOf, useOps, hhmm } from "../board/store.js";
import { run, aboutOf, dayWords } from "../board/ops.js";
import { copyText, toast } from "../link.js";
import { Field } from "./opdialog.js";
import { Modal, closeDialog } from "./modals.js";

const WAITING = { preparing: "It is being prepared…", acting: "It is being done…", held: "It waits for the limits…", done: "It is done.", dropped: "It was dropped." };

/** A kept brief as Markdown: its one part as written, or each part under its label. */
export function briefText(r, t) {
  const parts = (t.draft || []).filter((p) => String(r.draft?.[p.name] || "").trim());
  if (parts.length === 1) return String(r.draft[parts[0].name]).trim() + "\n";
  return parts.map((p) => `## ${p.label}\n\n${String(r.draft[p.name]).trim()}\n`).join("\n");
}

/** A brief's page, read-only: each draft part under its label, as written (Markdown, not rendered). */
function Page({ r, t, name = "" }) {
  const parts = (t.draft || []).filter((p) => String(r.draft?.[p.name] || "").trim());
  if (!parts.length) return html`<p class="ok-tone-muted">Its text is no longer kept: a newer one replaced it, or its days passed.</p>`;
  return parts.map((p) => html`<div key=${p.name} class="shell-field" data-part=${p.name}>
    ${parts.length > 1 && html`<span class="ok-font-label">${p.label}</span>`}
    <div class="shell-brief" tabindex="0" aria-label=${name ? `${name}: ${p.label}` : p.label}>${r.draft[p.name]}</div></div>`);
}

/** A kept brief: read-only, with Copy (Markdown to the clipboard); *by itself* when it was kept so. */
function KeptDialog({ r, t }) {
  const about = aboutOf(r, t);
  const text = briefText(r, t);
  const copy = () => { copyText(text); toast("Copied as Markdown: it is yours to paste"); };
  return html`<${Modal} title=${`${t.title}${about && ` · ${about}`}`} onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Close</button>
      <button type="button" class="ork-btn primary" disabled=${!text.trim()} title="Copies it as Markdown, for you to paste where you need it" onClick=${copy}>Copy</button>`}>
    <div class="shell-form" data-op=${r.id} data-kept>
      <p class="ok-font-status ok-tone-muted">Kept ${dayWords(r.done_at || r.at)} ${hhmm(r.done_at || r.at)}${r.alone && html` <span class="board-chip" data-by-itself="true">by itself</span>`}.
        For you alone: Orkboard never posts, sends or shows it to anyone.</p>
      <${Page} r=${r} t=${t} />
    </div>
  <//>`;
}

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
      foot=${html`<button type="button" class="ork-btn" disabled=${busy} onClick=${() => go("ops.drop", {})}>Drop</button>
        <button type="button" class="ork-btn" disabled=${busy} title="Adds a new operation with the same form" onClick=${() => go("ops.again", {})}>Add again</button>
        ${r.acted === false && html`<button type="button" class="ork-btn primary" disabled=${busy} onClick=${() => go("ops.retry", {})}>Try again</button>`}`}>
      <div class="shell-form" data-op=${r.id}>
        <p class="ok-tone-error" role="alert">${r.why || "It failed"}</p>
        ${r.acted !== false && html`<p class="ok-font-status ok-tone-muted">It may have been done: look in the tool before you add it again.</p>`}
      </div>
    <//>`;
  }
  if (r.state === "done" && r.brief) return html`<${KeptDialog} r=${r} t=${t} />`;
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
  const brief = !!t.brief;
  const last = brief && r.follows ? runOf(r.follows) : null;
  const about = brief ? aboutOf(r, t) : "";
  const foot = brief
    ? html`<button type="button" class="ork-btn danger" disabled=${busy} title="Throws it away: nothing is kept" onClick=${() => go("ops.drop", {})}>Drop</button>
      <button type="button" class="ork-btn" data-act="prepare" disabled=${busy} title="Prepares it again with the form as it is now; nothing is kept yet"
        onClick=${() => go("ops.prepare", sent())}>Prepare again</button>
      <button type="button" class="ork-btn primary" data-act="keep" disabled=${busy || again}
        title=${again ? "The form changed: Prepare again first" : "Keeps the page as you corrected it, for you alone: nothing is posted or sent"}
        onClick=${() => go("ops.keep", { draft: sent().draft })}>${t.act_label}</button>`
    : html`<button type="button" class="ork-btn danger" disabled=${busy} title="Throws it away: nothing is done" onClick=${() => go("ops.drop", {})}>Drop</button>
      <button type="button" class="ork-btn primary" data-act=${again ? "prepare" : "act"} disabled=${busy}
        title=${again ? "Prepares it again with the form as changed; nothing is done yet" : `${t.act_label}: this is done at once`}
        onClick=${() => go(again ? "ops.prepare" : "ops.act", sent())}>${again ? "Prepare again" : t.act_label}</button>`;
  return html`<${Modal} title=${`${t.title}${about && ` · ${about}`}`} onClose=${closeDialog} wide=${true} foot=${foot}>
    <div class="shell-form board-check" data-op=${r.id} data-brief=${brief ? "true" : null}>
      ${r.why && html`<p class="ok-font-status ok-tone-muted" data-check="why">${r.why}</p>`}
      ${r.doubts.length > 0 && html`<ul class="board-doubts" aria-label="Doubts">${r.doubts.map((d, n) => html`<li key=${n}><span aria-hidden="true">⚠</span> ${d}</li>`)}</ul>`}
      ${r.found.length > 0 && html`<div class="shell-field" role="group" aria-label="What was found"><span class="ok-font-label">What was found</span>
        <dl class="board-found">${r.found.map((x, n) => html`<div key=${n}><dt>${x.label}</dt><dd>${x.value}</dd></div>`)}</dl></div>`}
      ${last && html`<details class="shell-lasttime" data-last-time=${last.id}><summary>Last time · kept ${dayWords(last.done_at || last.at)}</summary>
        <${Page} r=${last} t=${t} name="Last time" /></details>`}
      ${t.draft.map((p) => html`<${Field} key=${p.name} f=${p} value=${part(p)} rows=${brief && p.type === "long" ? 16 : 4} onInput=${(v) => setDraft({ ...draft, [p.name]: v })} />`)}
      ${hasAt.map((f) => html`<${Field} key=${f.name} f=${f} value=${value(f)} onInput=${(v) => setFields({ ...fields, [f.name]: v })} />`)}
      ${noAt.length > 0 && html`<div class="shell-field" role="group" aria-label="The form"><span class="ok-font-label">The form</span>
        <span class="ok-font-status ok-tone-muted">Changing one of these prepares it again.</span>
        ${noAt.map((f) => html`<${Field} key=${f.name} f=${f} value=${value(f)} onInput=${(v) => setFields({ ...fields, [f.name]: v })} />`)}</div>`}
    </div>
  <//>`;
}
