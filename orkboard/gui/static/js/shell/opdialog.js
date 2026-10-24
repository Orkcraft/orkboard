// Operations' dialogs (docs/specs/38-operations.md §10): a template's form (New…), the gear (Target, clean checks, a day's cap,
// the servers) and a template's rules. The check of one operation is shell/opcheck.js. A brief (docs/specs/66-team-briefs.md §7):
// its form says what a template about people reads and may be prepared before a meeting on its own (a standing brief, set or
// changed here); Forget… asks once and removes everything kept about one value; the gear keeps the last 1:1 brief N days.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { ask, ops, templateOf, refreshOps, useOps } from "../board/store.js";
import { TARGETS } from "../board/target.js";
import { run, ReadsLine } from "../board/ops.js";
import { toast } from "../link.js";
import { Modal, closeDialog } from "./modals.js";

const KEEP = "orkboard.opform.";                // a form left with typed text is kept per template, on this device
const kept = (name) => { try { return JSON.parse(localStorage.getItem(KEEP + name) || "{}") || {}; } catch { return {}; } };
const keep = (name, values) => { try { if (values) localStorage.setItem(KEEP + name, JSON.stringify(values)); else localStorage.removeItem(KEEP + name); } catch { /* the form still works */ } };

/** A field of a template's form: text, a box (long) or a select (choice); `hint` is its placeholder. A brief's draft is a
 *  page (`rows` more). */
export function Field({ f, value, onInput, label = f.label, rows = 4 }) {
  const common = { class: "ork-field", "aria-label": label, value, placeholder: f.hint || "", onInput: (e) => onInput(e.target.value) };
  return html`<label class="shell-field" data-field=${f.name}><span class="ok-font-label">${label}${f.required ? " *" : ""}</span>
    ${f.type === "long" ? html`<textarea ...${common} rows=${rows}></textarea>`
      : f.type === "choice" ? html`<select class="ork-field" aria-label=${label} value=${value} onChange=${(e) => onInput(e.target.value)}>
        ${f.required || !f.default ? html`<option value="">—</option>` : null}
        ${(f.options || []).map((o) => html`<option key=${o} value=${o}>${o}</option>`)}</select>`
      : html`<input ...${common} />`}</label>`;
}

const DAYS = [["Mon", "Monday"], ["Tue", "Tuesday"], ["Wed", "Wednesday"], ["Thu", "Thursday"], ["Fri", "Friday"], ["Sat", "Saturday"], ["Sun", "Sunday"]];
const WEEKDAYS = [0, 1, 2, 3, 4];

/** The days, the meeting's time and the minutes before: a standing brief's schedule as the host takes it, or null. */
function scheduleOf(when) {
  const before = Number(when.before);
  if (!when.days.length || !/^([01]\d|2[0-3]):[0-5]\d$/.test(when.at) || !Number.isInteger(before) || before < 0 || before > 240) return null;
  return { days: [...when.days].sort(), at: when.at, before };
}

/** Prepare before…: seven day toggles, the meeting's time, the minutes before it (spec 66 §3). */
function Schedule({ when, onChange, onClose }) {
  const flip = (d) => onChange({ ...when, days: when.days.includes(d) ? when.days.filter((x) => x !== d) : [...when.days, d] });
  return html`<div class="shell-field" role="group" aria-label="Prepare before the meeting" data-schedule>
    <span class="ok-font-label">Prepare before the meeting</span>
    <div class="shell-seg shell-days" role="group" aria-label="Days of the week">${DAYS.map(([short, day], d) => html`<label key=${d}
      class=${`shell-seg__one${when.days.includes(d) ? " is-on" : ""}`}><input type="checkbox" class="gui-onb__hide" aria-label=${day}
      checked=${when.days.includes(d)} onChange=${() => flip(d)} />${short}</label>`)}</div>
    <div class="shell-when">
      <label class="shell-when__one"><span>The meeting at</span>
        <input class="ork-field" type="time" aria-label="The meeting's time" value=${when.at} onInput=${(e) => onChange({ ...when, at: e.target.value })} /></label>
      <label class="shell-when__one"><input class="ork-field board-num" type="number" min="0" max="240" aria-label="Minutes before" value=${when.before}
        onInput=${(e) => onChange({ ...when, before: e.target.value })} /><span>minutes before</span></label>
      ${onClose && html`<button type="button" class="board-link" onClick=${onClose}>No schedule</button>`}</div>
    <span class="ok-font-status ok-tone-muted">On these days, that many minutes before the meeting, it is prepared with this form as if you pressed Add:
      it waits for the limits as any other does, then at your check.</span>
  </div>`;
}

export function OpFormDialog({ template, standing = "" }) {
  const o = useOps();
  const t = templateOf(template);
  const item = standing ? (o?.standing || []).find((x) => x.id === standing) : null;
  const start = () => Object.fromEntries((t?.fields || []).map((f) => [f.name, f.default ?? ""]));
  const [values, setValues] = useState(() => ({ ...start(), ...(item ? item.fields : kept(template)) }));
  const [when, setWhen] = useState(() => (item ? { days: item.days, at: item.at, before: item.before } : null));
  const [busy, setBusy] = useState(false);
  if (!t || (standing && !item)) {
    return html`<${Modal} title="New operation" onClose=${closeDialog}><p class="ok-tone-muted">${t ? "This standing brief is gone." : "This template is gone."}</p><//>`;
  }
  const typed = () => {                                       // what the person changed from what the form began with
    const base = start();
    const got = Object.fromEntries(Object.entries(values).filter(([k, v]) => String(v).trim() && v !== base[k]));
    return Object.keys(got).length ? values : null;
  };
  const close = () => { if (!item) keep(template, typed()); closeDialog(); };
  const missing = t.fields.some((f) => f.required && !String(values[f.name] || "").trim());
  const plan = when && scheduleOf(when);
  const send = async (name, args) => {
    if (missing || busy) return;
    setBusy(true);
    const fields = Object.fromEntries(Object.entries(values).filter(([, v]) => String(v).trim()));
    const got = await ask(name, { ...args, fields });
    setBusy(false);
    if (!got?.id && !got?.ok) return;
    if (!item) keep(template, null);
    closeDialog();
    refreshOps();
  };
  const add = () => send("ops.add", { template });
  const schedule = () => plan && (item ? send("ops.standing_change", { id: item.id, ...plan }) : send("ops.standing_add", { template, ...plan }));
  const submit = (e) => { e?.preventDefault(); if (when) schedule(); else add(); };
  const foot = item
    ? html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="op-form" class="ork-btn primary" disabled=${missing || busy || !plan}>Save the changes</button>`
    : when
      ? html`<button type="button" class="ork-btn" disabled=${missing || busy} title="Prepares it once, now; no schedule is kept" onClick=${add}>Add</button>
        <button type="submit" form="op-form" class="ork-btn primary" disabled=${missing || busy || !plan}
          title="Keeps the schedule: it is prepared on its own before each meeting">Prepare before each meeting</button>`
      : html`${t.brief && html`<button type="button" class="ork-btn" title="Days and a time: it is prepared on its own before the meeting"
          onClick=${() => setWhen({ days: WEEKDAYS, at: "", before: 30 })}>Prepare before…</button>`}
        <button type="submit" form="op-form" class="ork-btn primary" disabled=${missing || busy}
          title=${`Adds it to Operations: it is prepared at once, then it waits at your check`}>Add</button>`;
  return html`<${Modal} title=${t.title} onClose=${close} wide=${true} foot=${foot}>
    <form id="op-form" class="shell-form" data-template=${template} data-standing=${item ? item.id : null} onSubmit=${submit}>
      ${t.people && t.reads && html`<${ReadsLine} reads=${t.reads} />`}
      ${t.fields.map((f) => html`<${Field} key=${f.name} f=${f} value=${values[f.name] ?? ""} onInput=${(v) => setValues({ ...values, [f.name]: v })} />`)}
      ${when && html`<${Schedule} when=${when} onChange=${setWhen} onClose=${item ? null : () => setWhen(null)} />`}
      <p class="ok-font-status ok-tone-muted">${t.brief ? "It reads, then prepares a page for you alone: nothing is posted, sent or changed anywhere. You read it before you keep it."
        : `Nothing is done yet: it is prepared first, and you check it before ${String(t.act_label || "it is done").toLowerCase()}.`}</p>
    </form>
  <//>`;
}

/** Forget… (spec 66 §2): a field for the value (a person's name, a team), then the one question; everything kept of it goes. */
export function OpForgetDialog({ template }) {
  const o = useOps();
  const t = templateOf(template);
  const [value, setValue] = useState("");
  const [sure, setSure] = useState(false);
  const [busy, setBusy] = useState(false);
  if (!t?.forget) return html`<${Modal} title="Forget" onClose=${closeDialog}><p class="ok-tone-muted">This template keeps nothing by name.</p><//>`;
  const v = value.trim();
  const known = [...new Set((o?.runs || []).filter((r) => r.template === template).map((r) => String(r.fields?.[t.forget.field] || "").trim()).filter(Boolean))];
  const forget = async () => {
    setBusy(true);
    const got = await run("ops.forget", { template, value: v });
    setBusy(false);
    if (!got) return;
    toast(got.removed ? `Forgot ${v}: ${got.removed} removed from ${t.title}` : `Nothing was kept about ${v} in ${t.title}`);
    closeDialog();
  };
  return html`<${Modal} title=${`Forget: ${t.title}`} onClose=${closeDialog}
    foot=${sure ? html`<button type="button" class="ork-btn" onClick=${() => setSure(false)}>Keep it</button>
        <button type="button" class="ork-btn danger" disabled=${busy} onClick=${forget}>Forget everything</button>`
      : html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
        <button type="submit" form="op-forget" class="ork-btn danger" disabled=${!v}>Forget…</button>`}>
    ${sure ? html`<p class="shell-modal__text" role="alert">Forget everything kept about <b>${v}</b> in ${t.title}? This cannot be undone.</p>`
      : html`<form id="op-forget" class="shell-form" onSubmit=${(e) => { e.preventDefault(); if (v) setSure(true); }}>
        <label class="shell-field"><span class="ok-font-label">${t.forget.label}</span>
          <input class="ork-field" autofocus list="op-forget-known" aria-label=${t.forget.label} value=${value} onInput=${(e) => setValue(e.target.value)} />
          <datalist id="op-forget-known">${known.map((k) => html`<option key=${k} value=${k} />`)}</datalist></label>
        <p class="ok-font-status ok-tone-muted">Every brief of ${t.title} made with this in ${t.forget.label}, kept or not, with its form and what it read, is removed now.
          Write it as on the form: capitals and spaces around it do not matter.</p></form>`}
  <//>`;
}

export function OpSettingsDialog() {
  const o = useOps();
  const [servers, setServers] = useState(null);
  const [typed, setTyped] = useState({});        // a number as the person types it, kept over a refresh until it is saved
  useEffect(() => { ask("ops.servers").then((got) => setServers(got?.servers || [])); }, []);
  const s = o?.settings || {};
  const set = async (change) => { const got = await run("ops.set", change); if (got && ops.value) ops.value = { ...ops.value, settings: got }; };
  const needed = Object.entries(o?.servers_needed || {});
  const number = (key, lo, hi, label, after) => html`<label class="board-row" data-setting=${key}>
    <span>${label}</span>
    <input class="ork-field board-num" type="number" min=${lo} max=${hi} value=${typed[key] ?? s[key]} aria-label=${after}
      onInput=${(e) => setTyped({ ...typed, [key]: e.target.value })}
      onChange=${(e) => {
        const n = Number(e.target.value);
        const done = () => setTyped((t) => { const { [key]: _saved, ...rest } = t; return rest; });
        if (Number.isInteger(n) && n >= lo && n <= hi) set({ [key]: n }).then(done); else done();
      }} />
    <span>${{ trust_after: "clean checks", follow_days: "days" }[key] || "a day"}</span></label>`;
  return html`<${Modal} title="Operations settings" onClose=${closeDialog} foot=${html`<button type="button" class="ork-btn primary" onClick=${closeDialog}>Done</button>`}>
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
      ${(o?.templates || []).some((t) => t.follow) && html`<div class="shell-field">
        ${number("follow_days", 14, 365, "Keep the last 1:1 brief for", "Days the last 1:1 brief is kept")}
        <span class="ok-font-status ok-tone-muted">The next one starts from it (Last time); after that many days it starts afresh, and its text goes.</span></div>`}
      ${needed.map(([key, word]) => {
        const now = s.servers?.[key] || "";
        const list = servers || [];
        return html`<label class="shell-field" key=${key} data-server=${key}><span class="ok-font-label">${word} server</span>
          <select class="ork-field" aria-label=${`${word} server`} value=${now} onChange=${(e) => set({ servers: { [key]: e.target.value } })}>
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
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="button" class="ork-btn primary" disabled=${text === null || busy || (text || "").length > 4000} onClick=${save}>Save the rules</button>`}>
    <div class="shell-form">
      <label class="shell-field"><span class="ok-font-label">Rules</span>
        <textarea class="ork-field" rows="10" aria-label="Rules" value=${text ?? ""} disabled=${text === null} placeholder="One rule a line, such as: Always put the epic in the title"
          onInput=${(e) => setText(e.target.value)}></textarea></label>
      <p class="ok-font-status ok-tone-muted">${(text || "").length} of 4000 characters. Every call of this template reads its rules. Saving changes only the rules, not whether it goes by itself.</p>
    </div>
  <//>`;
}
