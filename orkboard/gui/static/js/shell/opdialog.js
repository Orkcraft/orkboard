// Operations' dialogs (docs/specs/38-operations.md §10): a template's form (New…), the gear (Target, clean checks, a day's cap,
// the servers) and a template's rules. The check of one operation is shell/opcheck.js.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { ask, ops, templateOf, refreshOps, useOps } from "../board/store.js";
import { TARGETS } from "../board/target.js";
import { run } from "../board/ops.js";
import { Modal, closeDialog } from "./modals.js";

const KEEP = "orkboard.opform.";                // a form left with typed text is kept per template, on this device
const kept = (name) => { try { return JSON.parse(localStorage.getItem(KEEP + name) || "{}") || {}; } catch { return {}; } };
const keep = (name, values) => { try { if (values) localStorage.setItem(KEEP + name, JSON.stringify(values)); else localStorage.removeItem(KEEP + name); } catch { /* the form still works */ } };

/** A field of a template's form: text, a box (long) or a select (choice); `hint` is its placeholder. */
export function Field({ f, value, onInput, label = f.label }) {
  const common = { class: "ok-input", "aria-label": label, value, placeholder: f.hint || "", onInput: (e) => onInput(e.target.value) };
  return html`<label class="shell-field" data-field=${f.name}><span class="ok-font-label">${label}${f.required ? " *" : ""}</span>
    ${f.type === "long" ? html`<textarea ...${common} rows="4"></textarea>`
      : f.type === "choice" ? html`<select class="ok-input" aria-label=${label} value=${value} onChange=${(e) => onInput(e.target.value)}>
        ${f.required || !f.default ? html`<option value="">—</option>` : null}
        ${(f.options || []).map((o) => html`<option key=${o} value=${o}>${o}</option>`)}</select>`
      : html`<input ...${common} />`}</label>`;
}

export function OpFormDialog({ template }) {
  useOps();
  const t = templateOf(template);
  const start = () => Object.fromEntries((t?.fields || []).map((f) => [f.name, f.default ?? ""]));
  const [values, setValues] = useState(() => ({ ...start(), ...kept(template) }));
  const [busy, setBusy] = useState(false);
  if (!t) return html`<${Modal} title="New operation" onClose=${closeDialog}><p class="ok-tone-muted">This template is gone.</p><//>`;
  const typed = () => {                                       // what the person changed from what the form began with
    const base = start();
    const got = Object.fromEntries(Object.entries(values).filter(([k, v]) => String(v).trim() && v !== base[k]));
    return Object.keys(got).length ? values : null;
  };
  const close = () => { keep(template, typed()); closeDialog(); };
  const missing = t.fields.some((f) => f.required && !String(values[f.name] || "").trim());
  const add = async (e) => {
    e?.preventDefault();
    if (missing || busy) return;
    setBusy(true);
    const fields = Object.fromEntries(Object.entries(values).filter(([, v]) => String(v).trim()));
    const got = await ask("ops.add", { template, fields });
    setBusy(false);
    if (!got?.id) return;
    keep(template, null);
    closeDialog();
    refreshOps();
  };
  return html`<${Modal} title=${t.title} onClose=${close} wide=${true}
    foot=${html`<button type="submit" form="op-form" class="ok-btn primary" disabled=${missing || busy}
      title=${`Adds it to Operations: it is prepared at once, then it waits at your check`}>Add</button>`}>
    <form id="op-form" class="shell-form" data-template=${template} onSubmit=${add}>
      ${t.fields.map((f, n) => html`<${Field} key=${f.name} f=${f} value=${values[f.name] ?? ""} onInput=${(v) => setValues({ ...values, [f.name]: v })} />`)}
      <p class="ok-font-status ok-tone-muted">Nothing is done yet: it is prepared first, and you check it before ${String(t.act_label || "it is done").toLowerCase()}.</p>
    </form>
  <//>`;
}

export function OpSettingsDialog() {
  const o = useOps();
  const [servers, setServers] = useState(null);
  useEffect(() => { ask("ops.servers").then((got) => setServers(got?.servers || [])); }, []);
  const s = o?.settings || {};
  const set = async (change) => { const got = await run("ops.set", change); if (got && ops.value) ops.value = { ...ops.value, settings: got }; };
  const needed = Object.entries(o?.servers_needed || {});
  const number = (key, lo, hi, label, after) => html`<label class="board-row" data-setting=${key}>
    <span>${label}</span>
    <input class="ok-input board-num" type="number" min=${lo} max=${hi} value=${s[key]} aria-label=${after}
      onChange=${(e) => { const n = Number(e.target.value); if (Number.isInteger(n) && n >= lo && n <= hi) set({ [key]: n }); }} />
    ${key === "trust_after" ? html`<span>clean checks</span>` : html`<span>a day</span>`}</label>`;
  return html`<${Modal} title="Operations settings" onClose=${closeDialog} foot=${html`<button type="button" class="ok-btn primary" onClick=${closeDialog}>Done</button>`}>
    <div class="shell-form">
      <div class="shell-field" role="group" aria-label="Target"><span class="ok-font-label">Target</span>
        <div class="shell-seg">${TARGETS.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${s.target === id ? " is-on" : ""}`}>
          <input type="radio" name="op-target" class="gui-onb__hide" checked=${s.target === id} onChange=${() => set({ target: id })} />${name}</label>`)}</div>
        <span class="ok-font-status ok-tone-muted">${(TARGETS.find(([id]) => id === s.target) || TARGETS[1])[2]}. It picks the model and the reasoning of every operation's calls.</span></div>
      <div class="shell-field">
        ${number("trust_after", 1, 5, "Goes by itself after", "Clean checks before it goes by itself")}
        <span class="ok-font-status ok-tone-muted">A template you passed that many times with no correction does its work without asking you.</span>
        ${number("daily_alone", 1, 100, "By itself at most", "At most by itself a day")}
        <span class="ok-font-status ok-tone-muted">Past that, the rest of the day's operations wait at your check.</span></div>
      ${needed.map(([key, word]) => {
        const now = s.servers?.[key] || "";
        const list = servers || [];
        return html`<label class="shell-field" key=${key} data-server=${key}><span class="ok-font-label">${word} server</span>
          <select class="ok-input" aria-label=${`${word} server`} value=${now} onChange=${(e) => set({ servers: { [key]: e.target.value } })}>
            <option value="">not connected</option>
            ${[...new Set([...(now ? [now] : []), ...list])].map((n) => html`<option key=${n} value=${n}>${n}</option>`)}</select></label>`;
      })}
      ${needed.length > 0 && html`<p class="ok-font-status ok-tone-muted">The server a template reads and writes with, as <code>claude mcp list</code> names it.</p>`}
    </div>
  <//>`;
}

export function OpRulesDialog({ template }) {
  useOps();
  const t = templateOf(template);
  const [text, setText] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { ask("ops.rules", { template }).then((got) => setText(got ? got.text || "" : "")); }, [template]);
  const save = async () => {
    setBusy(true);
    const got = await run("ops.rules_save", { template, text });
    setBusy(false);
    if (got) closeDialog();
  };
  return html`<${Modal} title=${`Rules: ${t?.title || template}`} onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Cancel</button>
      <button type="button" class="ok-btn primary" disabled=${text === null || busy || (text || "").length > 4000} onClick=${save}>Save the rules</button>`}>
    <div class="shell-form">
      <label class="shell-field"><span class="ok-font-label">Rules</span>
        <textarea class="ok-input" rows="10" aria-label="Rules" value=${text ?? ""} disabled=${text === null} placeholder="One rule a line, such as: Always put the epic in the title"
          onInput=${(e) => setText(e.target.value)}></textarea></label>
      <p class="ok-font-status ok-tone-muted">${(text || "").length} of 4000 characters. Every call of this template reads its rules. Saving changes only the rules, not whether it goes by itself.</p>
    </div>
  <//>`;
}
