// The projects (docs/specs/37-board-and-line.md §8, docs/specs/69-parties-in-the-column.md §1): the switcher that heads the left column, as wide as it (it was the top bar's; the open projects with their counts,
// Recent, Open folder…, Close project), the Open folder dialog, the start screen when no project is open, and the dialog
// that asks before a project with running tasks is closed. The host sends `projects` with every snapshot (projects.list),
// so the counts are live; showing another project stops nothing in the others.
import { useEffect, useRef, useState } from "preact/hooks";
import { computed } from "@preact/signals";
import { html, cls } from "../html.js";
import { Chev } from "../orkui.js";
import { town, command, toast } from "../link.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { leaving } from "./store.js";
import { Operations } from "../board/ops.js";

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

const PICK_POLL_MS = 300;

/** The system's folder dialog (gui/folder_dialog.py): the host opens it, the page asks what came of it while `alive`.
 *  {state: "done", path} | {state: "none"} (cancelled) | {state: "error", why} (no dialog here: the path is typed). */
export async function chooseFolder(start, alive) {
  let token;
  try { ({ token } = await command("folders.pick", { start })); } catch { return { state: "error", why: "" }; }
  while (alive.current) {
    await new Promise((r) => setTimeout(r, PICK_POLL_MS));
    let got;
    try { got = await command("folders.picked", { token }); } catch { return { state: "error", why: "" }; }
    if (got?.state !== "open") return got || { state: "error", why: "" };
  }
  return { state: "none" };
}

export function OpenFolderDialog() {
  const [path, setPath] = useState("");
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [nogit, setNogit] = useState("");        // the folder just opened that has no git
  const alive = useRef(true);
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
  // As an IDE's Open Folder: the system's dialog at once (quiet when there is none here), Choose… to open it again;
  // the folder chosen opens, and the path can still be typed or a recent one taken.
  const choose = async (quiet = false) => {
    if (choosing) return;
    setChoosing(true);
    setWhy("");
    const got = await chooseFolder(path.trim(), alive);
    if (!alive.current) return;
    setChoosing(false);
    if (got.state === "done" && got.path) { setPath(got.path); go(null, got.path); }
    else if (got.state === "error" && got.why && !quiet) setWhy(got.why);
  };
  useEffect(() => { choose(true); return () => { alive.current = false; }; }, []);
  if (nogit) {
    return html`<${Modal} title="Start git here?" onClose=${closeDialog}
      foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Not now</button>
        <button type="button" class="ork-btn primary" onClick=${async () => { if (await startGit(nogit)) closeDialog(); }}>Start git here</button>`}>
      <p>This folder has no git. The Board works on a repository, so its tasks need one.</p>
      <p class="ok-font-status ok-tone-muted">Start git here makes a first commit of the folder's files as they are, and changes nothing else.</p>
    <//>`;
  }
  return html`<${Modal} title="Open folder" onClose=${closeDialog}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="open-folder-form" class="ork-btn primary" disabled=${!path.trim() || busy}>Open folder</button>`}>
    <form id="open-folder-form" class="shell-form" onSubmit=${go}>
      <div class="shell-field"><label class="ok-font-label" for="open-folder-path">Folder</label>
        <div class="shell-pick"><input id="open-folder-path" class="ork-field" autofocus value=${path} aria-label="Folder"
          placeholder="The path of a project's folder, such as ~/code/shop" onInput=${(e) => { setPath(e.target.value); setWhy(""); }} />
          <button type="button" class="ork-btn" disabled=${choosing || busy} onClick=${() => choose()}>Choose…</button></div>
        ${choosing && html`<p class="ok-font-status ok-tone-muted" role="status">Choose the folder in the dialog that opened, or type its path.</p>`}</div>
      ${why && html`<p class="ok-tone-error" role="alert">${why}</p>`}
      <p class="ok-font-status ok-tone-muted">The folder becomes a project: its parties, goals and tasks are kept in it, apart from your other projects.</p>
      ${recent.length > 0 && html`<div class="shell-field" role="group" aria-label="Recent"><span class="ok-font-label">Recent</span>
        <div class="shell-menu__list">${recent.map((r) => html`<button type="button" key=${r.path} class="shell-menu__item" title=${r.path}
          onClick=${(e) => go(e, r.path)}>${r.name} <span class="ok-tone-muted">${r.path}</span></button>`)}</div></div>`}
    </form>
  <//>`;
}

export function CloseProjectDialog({ path, name, running }) {
  const [busy, setBusy] = useState(false);
  return html`<${Modal} title="Close project" onClose=${closeDialog}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Keep it open</button>
      <button type="button" class="ork-btn danger" disabled=${busy} onClick=${async () => { setBusy(true); await closeProject(path, true); closeDialog(); }}>Stop them and close</button>`}>
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
    <button class="ork-btn shell-proj__btn" aria-haspopup="menu" aria-expanded=${open} title=${cur?.path || ""}
      onClick=${() => setOpen(!open)}><b>${cur ? cur.name : "No project"}</b><${Chev} /></button>
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
    <p class="ok-tone-muted">A project is a repository's folder. Its parties, goals and tasks are kept in it.</p>
    <p><button class="ork-btn primary" onClick=${() => openDialog("open-folder")}>Open folder…</button>
      <span class="ok-tone-muted"> Ctrl+O</span></p>
    ${recent.length > 0 && html`<section class="shell-start__recent" aria-label="Recent"><h2 class="ok-font-label">Recent</h2>
      <ul>${recent.map((r) => html`<li key=${r.path}><button class="board-link" title=${r.path} onClick=${() => openFolder(r.path)}>${r.name}</button>
        <span class="ok-font-status ok-tone-muted">${r.path}</span></li>`)}</ul></section>`}
    <section class="shell-start__ops" aria-label="Operations"><${Operations} withNew=${true} /></section>
  </main>`;
}
