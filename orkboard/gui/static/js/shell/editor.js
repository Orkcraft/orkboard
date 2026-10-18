// The editor (docs/specs/37-board-and-line.md §8): a plain monospace text area for a Markdown or text file. Ctrl+S / ⌘S
// saves; leaving with changes asks (the shell's `leaving`); a save the host refuses says why in words — the file changed
// on disk since it was read (*changed on disk: reload*), it leaves the project, it is a Board page.
import { useEffect, useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { command, copyText } from "../link.js";
import { editing } from "./store.js";
import { Modal, closeDialog } from "./modals.js";

const CHANGED = "changed on disk: reload";

window.addEventListener("beforeunload", (e) => {         // closing the window with unsaved changes asks too
  if (editing.value?.dirty) { e.preventDefault(); e.returnValue = ""; }
});

export function Editor({ file, onSaved, onCancel, onReload }) {
  const [text, setText] = useState(file.text);
  const [mtime, setMtime] = useState(file.mtime);
  const [why, setWhy] = useState("");
  const [saving, setSaving] = useState(false);
  const now = useRef({});
  now.current = { text, mtime, saving };
  const dirty = text !== file.text;

  const save = async () => {
    const cur = now.current;
    if (cur.saving) return false;
    setSaving(true);
    setWhy("");
    try {
      const got = await command("files.write", { path: file.path, text: cur.text, mtime: cur.mtime });
      if (got?.error) { setWhy(got.error); return false; }
      setMtime(got.mtime);
      onSaved(cur.text, got.mtime);
      return true;
    } catch (e) {
      setWhy(e.message || "That file could not be saved");
      return false;
    } finally { setSaving(false); }
  };
  useEffect(() => {
    editing.value = { path: file.path, dirty, save };
  }, [file.path, dirty]);
  useEffect(() => () => { editing.value = null; }, []);
  const key = (e) => {
    if ((e.ctrlKey || e.metaKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "s") { e.preventDefault(); save(); }
  };
  return html`<div class="shell-edit">
    <div class="shell-edit__bar">
      <button class="ok-btn primary" disabled=${saving || !dirty} onClick=${save}>Save <span class="ok-tone-muted">Ctrl+S</span></button>
      <button class="ok-btn" onClick=${onCancel}>Cancel</button>
      ${dirty && html`<span class="ok-font-status ok-tone-muted">Unsaved changes</span>`}
    </div>
    ${why && html`<div class="shell-edit__why ok-tone-error" role="alert"><span>${why}</span>
      ${why === CHANGED && html`<button class="ok-btn" onClick=${onReload}>Reload</button>
        <button class="ok-btn" onClick=${() => copyText(text)}>Copy my text</button>`}</div>`}
    <textarea class="shell-edit__text" aria-label="Editor" spellcheck="false" autofocus value=${text} onKeyDown=${key}
      onInput=${(e) => setText(e.target.value)}></textarea>
  </div>`;
}

/** Asked when the person leaves a file with unsaved changes (`leaving` in shell/store.js). */
export function LeaveDialog({ then }) {
  const [busy, setBusy] = useState(false);
  const file = editing.value;
  return html`<${Modal} title="Unsaved changes" onClose=${closeDialog}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Keep editing</button>
      <button type="button" class="ok-btn danger" disabled=${busy} onClick=${() => { editing.value = null; closeDialog(); then(); }}>Discard changes</button>
      <button type="button" class="ok-btn primary" disabled=${busy} onClick=${async () => {
        setBusy(true);
        const ok = await file?.save();
        setBusy(false);
        if (ok) { editing.value = null; closeDialog(); then(); } else closeDialog();
      }}>Save and leave</button>`}>
    <p>${file?.path || "This file"} has changes you have not saved.</p>
  <//>`;
}
