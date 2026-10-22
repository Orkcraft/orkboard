// A to-do of a plan (docs/specs/35-goals-window.md §9): why it is asked, its steps, then its one input — a secret, a
// choice, a confirm or a file. `instructions` are steps only. A file goes as base64 in `ideas.todo`'s `file`
// (at most 5 MB); the host keeps it outside the repository.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { act, showPlan } from "./store.js";
import { Modal, closeDialog } from "./modals.js";

const FILE_MAX = 5 * 1024 * 1024;

const toBase64 = (file) => new Promise((resolve, reject) => {
  const r = new FileReader();
  r.onload = () => resolve(String(r.result).split(",")[1] || "");
  r.onerror = () => reject(r.error);
  r.readAsDataURL(file);
});

/** A leader's or an asker's name in a sentence: *the Taskmaster*, *Reviewer*. */
export const named = (name) => (name === "Taskmaster" || !name ? "the Taskmaster" : name);

/** A to-do's ways out (spec 54 §3.2), under its own input: a file *Describe it instead* (a field and *Send*) and *Go without it*; a choice *Let <leader> choose*; the rest
 *  *Go without it*. Each is quiet and acts at once, then `done`. `quick`: on the raised stop (its buttons), else in the dialog. */
export function TodoWays({ idea, todo, lead, agent, done = () => {}, quick = true }) {
  const [telling, setTelling] = useState(false), [words, setWords] = useState(""), [busy, setBusy] = useState(false);
  const look = quick ? "ork-btn quiet arena-hc__q" : "ork-btn quiet";
  const skip = async () => {
    setBusy(true);
    const got = await act("ideas.todo", { idea, id: todo.id, skip: true });
    setBusy(false);
    if (got) { toast(say(`Done: ${named(lead)}’s plan goes on without it.`)); done(); }
  };
  const send = async () => {
    if (!words.trim()) return;
    setBusy(true);
    const got = await act("ideas.todo", { idea, id: todo.id, done: true, words: words.trim() });
    setBusy(false);
    if (got) { toast(say(`Sent: the words go to ${named(agent || lead)}.`)); setTelling(false); setWords(""); done(); }
  };
  const without = (label) => html`<button type="button" class=${look} disabled=${busy} aria-label=${`${label}: ${todo.title}`}
    title="Its tasks run without it, and say so if they cannot" onClick=${skip}>${label}</button>`;
  if (todo.kind === "choice") return without(`Let ${named(lead)} choose`);
  if (todo.kind !== "file") return without("Go without it");
  return telling ? html`<div class=${quick ? "arena-hc__why" : "board-row"}>
      <input class="ork-field" value=${words} aria-label=${`What should it look like? ${todo.title}`} placeholder="What should it look like?" autofocus maxlength="2000"
        onInput=${(e) => setWords(e.target.value)} onKeyDown=${(e) => { if (e.key === "Enter") send(); }} />
      <button type="button" class=${look} disabled=${!words.trim() || busy} aria-label=${`Send: ${todo.title}`} onClick=${send}>Send</button>
      <button type="button" class=${look} onClick=${() => setTelling(false)}>Cancel</button></div>`
    : html`<button type="button" class=${look} aria-label=${`Describe it instead: ${todo.title}`} onClick=${() => setTelling(true)}>Describe it instead</button>${without("Go without it")}`;
}

export function TodoDialog({ idea, todo, lead }) {
  const [value, setValue] = useState("");
  const [file, setFile] = useState(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const done = async (extra = {}) => {
    if (busy) return;
    setBusy(true);
    const got = await act("ideas.todo", { idea, id: todo.id, done: true, ...extra });
    setBusy(false);
    if (got) closeDialog();
  };
  const pick = (f) => {
    setProblem("");
    if (f && f.size > FILE_MAX) { setFile(null); setProblem("The file is larger than 5 MB"); return; }
    setFile(f || null);
  };
  const sendFile = async () => {
    if (!file) return;
    await done({ file: { name: file.name, data: await toBase64(file) } });
  };
  const kind = todo.kind;
  return html`<${Modal} title=${todo.title} onClose=${closeDialog}
    foot=${html`<button type="button" class="ork-btn" onClick=${() => { closeDialog(); showPlan(idea, todo.id); }}>What waits for it</button>
      <button type="button" class="ork-btn" onClick=${closeDialog}>Later</button>
      ${(kind === "instructions" || kind === "confirm" || !["secret", "choice", "file"].includes(kind)) && html`<button type="button" class="ork-btn primary"
        disabled=${busy} onClick=${() => done()}>${kind === "instructions" ? "I did it" : "Done"}</button>`}`}>
    <div class="shell-form board-todo-dialog" data-kind=${kind}>
      ${todo.why && html`<p class="shell-brief">${todo.why}</p>`}
      ${todo.steps?.length > 0 && html`<div class="shell-field"><span class="ok-font-label">Steps</span>
        <ol class="board-steps">${todo.steps.map((s, n) => html`<li key=${n}>${s}</li>`)}</ol></div>`}
      ${kind === "secret" && html`<label class="shell-field"><span class="ok-font-label">The value</span>
        <input class="ork-field" type="password" autocomplete="off" autofocus value=${value} aria-label=${`Value of ${todo.title}`}
          placeholder=${say("Kept on this machine, never in a prompt")} onInput=${(e) => setValue(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && value) done({ value }); }} />
        <span><button type="button" class="ork-btn primary" disabled=${!value || busy} onClick=${() => done({ value })}>Keep it</button></span></label>`}
      ${kind === "choice" && html`<div class="shell-field"><span class="ok-font-label">Pick one</span>
        <div class="board-row">${(todo.choices || []).map((c) => html`<button type="button" key=${c} class="ork-btn" disabled=${busy}
          onClick=${() => done({ value: c })}>${c}</button>`)}</div></div>`}
      ${kind === "file" && html`<div class="shell-field"><span class="ok-font-label">The file</span>
        <input class="ork-field" type="file" aria-label=${`File: ${todo.title}`} accept=${(todo.accept || []).map((x) => (x.startsWith(".") ? x : `.${x}`)).join(",")}
          onChange=${(e) => pick(e.target.files?.[0])} />
        <span class="ok-font-status ok-tone-muted">${say("At most 5 MB. Kept on this machine, outside the repository, never in a prompt.")}</span>
        ${problem && html`<span class="ok-tone-error" role="alert">${problem}</span>`}
        <span><button type="button" class="ork-btn primary" disabled=${!file || busy} onClick=${sendFile}>Send the file</button></span></div>`}
      <div class="shell-field board-row board-todo-ways"><${TodoWays} idea=${idea} todo=${todo} lead=${lead} agent=${todo.by?.name} done=${closeDialog} quick=${false} /></div>
    </div>
  <//>`;
}
