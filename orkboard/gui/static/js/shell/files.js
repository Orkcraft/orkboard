// The Files pane (docs/specs/37-board-and-line.md §8): the project's tree one level at a time, folders folded, `.git/` and
// `.orkcraft/` never shown, git-ignored files behind a toggle; a click opens the file in the preview — Markdown rendered,
// code and text with line numbers, a binary or large file by its size with Open in the system. What may hold a secret is
// greyed and never read. The Git section (gitpane.js) sits under the tree.
import { useEffect, useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { html, cls } from "../html.js";
import { command } from "../link.js";
import { ask } from "../board/store.js";
import { preview, showFile, leaving } from "./store.js";
import { Editor } from "./editor.js";
import { GitSection } from "./gitpane.js";

const entries = signal({});               // folder ("" = the project) → its entries, one level
const expanded = signal(new Set());       // the folders open
const showIgnored = signal(false);
export const SECRET_HINT = "may hold secrets: open it in your own editor";

export async function loadDir(dir = "") {
  const got = await ask("files.tree", { ...(dir ? { dir } : {}), ...(showIgnored.value ? { ignored: true } : {}) });
  if (got) entries.value = { ...entries.value, [dir]: got.entries };
}

export function reloadTree() {
  const dirs = ["", ...expanded.value];
  return Promise.all(dirs.map(loadDir));
}

export function resetFiles() {
  entries.value = {};
  expanded.value = new Set();
}

async function toggle(dir) {
  const set = new Set(expanded.value);
  if (set.has(dir)) set.delete(dir);
  else { set.add(dir); if (!entries.value[dir]) await loadDir(dir); }
  expanded.value = set;
}

function Rows({ dir, depth }) {
  const list = entries.value[dir];
  if (!list) return depth ? html`<li class="shell-tree__note ok-tone-muted" style=${`padding-left:${depth * 14 + 8}px`}>Opening…</li>` : null;
  if (!list.length) return depth ? html`<li class="shell-tree__note ok-tone-muted" style=${`padding-left:${depth * 14 + 8}px`}>Empty</li>` : null;
  const on = preview.value?.kind === "file" ? preview.value.path : "";
  return list.map((e) => html`<li key=${e.path} role="none">
    <button role="treeitem" class=${cls("shell-tree__row", { "is-dir": e.dir, "is-secret": e.secret, "is-on": e.path === on })}
      style=${`padding-left:${depth * 14 + 8}px`} data-path=${e.path} aria-expanded=${e.dir ? expanded.value.has(e.path) : undefined}
      title=${e.secret ? `${e.name}: ${SECRET_HINT}` : e.path} onClick=${() => (e.dir ? toggle(e.path) : showFile(e.path))}>
      <span class="shell-tree__mark" aria-hidden="true">${e.dir ? (expanded.value.has(e.path) ? "▾" : "▸") : ""}</span>${e.name}${e.dir ? "/" : ""}</button>
    ${e.dir && expanded.value.has(e.path) && html`<ul role="group" class="shell-tree__list"><${Rows} dir=${e.path} depth=${depth + 1} /></ul>`}
  </li>`);
}

export function FilesPane() {
  useEffect(() => { reloadTree(); }, []);
  return html`<div class="shell-files">
    <div class="shell-files__bar">
      <label class="ok-check"><input type="checkbox" class="gui-onb__hide" checked=${showIgnored.value}
        onChange=${(e) => { showIgnored.value = e.target.checked; reloadTree(); }} />
        <i>${showIgnored.value ? "✓" : ""}</i><span>Show git-ignored files</span></label>
      <button class="shell-quiet" onClick=${reloadTree}>Refresh</button>
    </div>
    <ul role="tree" class="shell-tree" aria-label="Files"><${Rows} dir="" depth=${0} />
      ${entries.value[""] && !entries.value[""].length && html`<li class="shell-tree__note ok-tone-muted">This folder is empty.</li>`}</ul>
    <${GitSection} />
  </div>`;
}

const sizeWords = (n) => (n < 1024 ? `${n} bytes` : n < 1048576 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1048576).toFixed(1)} MB`);

/** A file's text with its line numbers beside it. */
export function Code({ text }) {
  const lines = text.split("\n");
  if (lines.length > 1 && lines[lines.length - 1] === "") lines.pop();
  return html`<div class="shell-code" aria-label="Code"><pre class="shell-code__nos" aria-hidden="true">${lines.map((_, i) => i + 1).join("\n")}</pre>
    <pre class="shell-code__text">${text}</pre></div>`;
}

/** The file in the preview: read when its path changes; Edit for Markdown and text. */
export function FileView({ path }) {
  const [f, setF] = useState(null);
  const [editingNow, setEditingNow] = useState(false);
  const load = async () => {
    const got = await ask("files.read", { path });
    setF(got || { path, kind: "gone" });
    return got;
  };
  useEffect(() => { setF(null); setEditingNow(false); load(); }, [path]);
  if (!f) return html`<p class="ok-tone-muted">Opening…</p>`;
  if (editingNow && f.text != null) {
    return html`<${Editor} file=${f} onCancel=${() => leaving(() => setEditingNow(false))}
      onReload=${async () => { await load(); setEditingNow(false); }}
      onSaved=${async () => { await load(); await reloadTree(); setEditingNow(false); }} />`;
  }
  const canEdit = f.kind === "markdown" || f.kind === "text";
  const head = html`<div class="shell-file__bar"><span class="ok-font-status ok-tone-muted">${sizeWords(f.size || 0)}</span>
    ${canEdit && html`<button class="ok-btn" onClick=${() => setEditingNow(true)}>Edit</button>`}</div>`;
  if (f.kind === "markdown") return html`${head}<div class="shell-md" data-kind="markdown" dangerouslySetInnerHTML=${{ __html: f.html || "" }}></div>`;
  if (f.kind === "text") return html`${head}<${Code} text=${f.text || ""} />`;
  if (f.kind === "secret") return html`<p class="ok-tone-muted" data-kind="secret">${path} ${SECRET_HINT}.</p>`;
  if (f.kind === "gone") return html`<p class="ok-tone-muted">That file cannot be shown.</p>`;
  return html`<div class="shell-binary" data-kind=${f.kind}><p>${f.kind === "large" ? "This file is larger than 1 MB" : "This is a binary file"}: ${sizeWords(f.size || 0)}.</p>
    <p><button class="ok-btn" onClick=${() => command("files.reveal", { path }).catch(() => {})}>Open in the system</button></p>
    <p class="ok-font-status ok-tone-muted">Opens it in the app your system uses for it.</p></div>`;
}
