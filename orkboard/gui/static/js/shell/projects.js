// The projects (docs/specs/37-board-and-line.md §8): the switcher that heads the top bar (the open projects with their counts,
// Recent, Open folder…, Close project), the Open folder dialog, the start screen when no project is open, and the dialog
// that asks before a project with running tasks is closed. The host sends `projects` with every snapshot (projects.list),
// so the counts are live; showing another project stops nothing in the others.
import { useEffect, useRef, useState } from "preact/hooks";
import { computed } from "@preact/signals";
import { html, cls } from "../html.js";
import { town, command, toast } from "../link.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { leaving } from "./store.js";

export const projectList = computed(() => town.value?.projects || { current: null, open: [], recent: [] });
/** Orkboard's host sends `projects`; Orkline's page (same shell) has one fixed project and none of this. */
export const projectsOn = computed(() => !!town.value?.projects);
export const currentProject = computed(() => {
  const p = projectList.value;
  return p.open.find((o) => o.path === p.current) || null;
});
const countsWords = (p) => [p.working ? `working ${p.working}` : "", p.needs_you ? `needs you ${p.needs_you}` : "",
  p.review ? `review ${p.review}` : ""].filter(Boolean).join(" · ") || "quiet";

/** Open a folder: a refusal comes back in words (the dialog shows it); a folder without git is offered Start git here. */
export async function openFolder(path) {
  let got;
  try { got = await command("projects.open", { path, device: "desktop" }); } catch { return { ok: false, error: "" }; }
  return got;
}

export function showProject(path) {
  return leaving(() => command("projects.use", { path }).catch(() => {}));
}

export async function closeProject(path, stop = false) {
  let got;
  try { got = await command("projects.close", { path, ...(stop ? { stop: true } : {}) }); } catch { return; }
  if (got?.running) {
    const name = projectList.value.open.find((o) => o.path === path)?.name || "the project";
    openDialog("close-project", { path, name, running: got.running });
  }
}

export async function startGit(path) {
  try {
    const got = await command("projects.start_git", { path });
    if (got?.error) { toast(got.error, "error"); return false; }
    toast(got.said || "Git is started", "information");
    return true;
  } catch { return false; }
}

export function OpenFolderDialog() {
  const [path, setPath] = useState("");
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [nogit, setNogit] = useState("");        // the folder just opened that has no git
  const recent = projectList.value.recent;
  const go = async (e, p = path) => {
    e?.preventDefault();
    if (!p.trim() || busy) return;
    setBusy(true);
    const got = await openFolder(p.trim());
    setBusy(false);
    if (!got.ok) { if (got.error) setWhy(got.error); return; }
    if (got.git === false) { setNogit(p.trim()); return; }
    closeDialog();
  };
  if (nogit) {
    return html`<${Modal} title="Start git here?" onClose=${closeDialog}
      foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Not now</button>
        <button type="button" class="ok-btn primary" onClick=${async () => { if (await startGit(nogit)) closeDialog(); }}>Start git here</button>`}>
      <p>This folder has no git. The Board works on a repository, so its tasks need one.</p>
      <p class="ok-font-status ok-tone-muted">Start git here makes a first commit of the folder's files as they are, and changes nothing else.</p>
    <//>`;
  }
  return html`<${Modal} title="Open folder" onClose=${closeDialog}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="open-folder-form" class="ok-btn primary" disabled=${!path.trim() || busy}>Open folder</button>`}>
    <form id="open-folder-form" class="shell-form" onSubmit=${go}>
      <label class="shell-field"><span class="ok-font-label">Folder</span>
        <input class="ok-input" autofocus value=${path} aria-label="Folder" placeholder="The path of a project's folder, such as ~/code/shop"
          onInput=${(e) => { setPath(e.target.value); setWhy(""); }} /></label>
      ${why && html`<p class="ok-tone-error" role="alert">${why}</p>`}
      <p class="ok-font-status ok-tone-muted">The folder becomes a project: its goals, ideas and tasks are kept in it, apart from your other projects.</p>
      ${recent.length > 0 && html`<div class="shell-field" role="group" aria-label="Recent"><span class="ok-font-label">Recent</span>
        <div class="shell-menu__list">${recent.map((r) => html`<button type="button" key=${r.path} class="shell-menu__item" title=${r.path}
          onClick=${(e) => go(e, r.path)}>${r.name} <span class="ok-tone-muted">${r.path}</span></button>`)}</div></div>`}
    </form>
  <//>`;
}

export function CloseProjectDialog({ path, name, running }) {
  const [busy, setBusy] = useState(false);
  return html`<${Modal} title="Close project" onClose=${closeDialog}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Keep it open</button>
      <button type="button" class="ok-btn danger" disabled=${busy} onClick=${async () => { setBusy(true); await closeProject(path, true); closeDialog(); }}>Stop them and close</button>`}>
    <p>${running} task${running === 1 ? " is" : "s are"} running in ${name}.</p>
    <p class="ok-font-status ok-tone-muted">Stopping them ends their work; what they wrote so far stays in their branches.</p>
  <//>`;
}

export function ProjectSwitcher() {
  const [open, setOpen] = useState(false);
  const box = useRef();
  const p = projectList.value, cur = currentProject.value;
  useEffect(() => {
    if (!open) return undefined;
    const away = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    const key = (e) => { if (e.key === "Escape") { setOpen(false); box.current?.querySelector("button")?.focus(); } };
    window.addEventListener("mousedown", away);
    window.addEventListener("keydown", key);
    return () => { window.removeEventListener("mousedown", away); window.removeEventListener("keydown", key); };
  }, [open]);
  const pick = (fn) => () => { setOpen(false); fn(); };
  if (!projectsOn.value) return null;
  return html`<span class="shell-proj" ref=${box}>
    <button class="ok-btn shell-proj__btn" aria-haspopup="menu" aria-expanded=${open} title=${cur?.path || ""}
      onClick=${() => setOpen(!open)}><b>${cur ? cur.name : "No project"}</b> <span aria-hidden="true">▾</span></button>
    ${open && html`<div class="shell-proj__menu" role="menu" aria-label="Projects">
      ${p.open.length > 0 && html`<div class="shell-proj__head ok-font-label">Open projects</div>`}
      ${p.open.map((o) => html`<button key=${o.path} role="menuitem" class=${cls("shell-menu__item shell-proj__one", { "is-on": o.path === p.current })}
        data-path=${o.path} title=${o.path} onClick=${pick(() => (o.path === p.current ? null : showProject(o.path)))}>
        <span class="shell-proj__name">${o.path === p.current ? "✓ " : ""}${o.name}</span>
        <span class="shell-proj__counts ok-tone-muted">${countsWords(o)}</span></button>`)}
      ${p.recent.length > 0 && html`<div class="shell-proj__head ok-font-label">Recent</div>`}
      ${p.recent.map((r) => html`<button key=${r.path} role="menuitem" class="shell-menu__item" title=${r.path}
        onClick=${pick(() => leaving(() => openFolder(r.path)))}>${r.name}</button>`)}
      <div class="shell-proj__sep"></div>
      <button role="menuitem" class="shell-menu__item" onClick=${pick(() => openDialog("open-folder"))}>Open folder… <span class="ok-tone-muted">Ctrl+O</span></button>
      ${cur && html`<button role="menuitem" class="shell-menu__item" onClick=${pick(() => leaving(() => closeProject(cur.path)))}>Close project</button>`}
    </div>`}
  </span>`;
}

/** No project is open: Open folder… and the recent ones. */
export function StartScreen() {
  const recent = projectList.value.recent;
  return html`<main class="shell-start" aria-label="Start">
    <h1>Open a project</h1>
    <p class="ok-tone-muted">A project is a repository's folder. Its goals, ideas and tasks are kept in it.</p>
    <p><button class="ok-btn primary" onClick=${() => openDialog("open-folder")}>Open folder…</button>
      <span class="ok-tone-muted"> Ctrl+O</span></p>
    ${recent.length > 0 && html`<section class="shell-start__recent" aria-label="Recent"><h2 class="ok-font-label">Recent</h2>
      <ul>${recent.map((r) => html`<li key=${r.path}><button class="board-link" title=${r.path} onClick=${() => openFolder(r.path)}>${r.name}</button>
        <span class="ok-font-status ok-tone-muted">${r.path}</span></li>`)}</ul></section>`}
  </main>`;
}
