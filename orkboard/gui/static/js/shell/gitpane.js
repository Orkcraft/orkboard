// The Git section of the Files pane (docs/specs/37-board-and-line.md §8): the branch (the work branch or main), ahead / behind
// its upstream, the changed files with their + / − (a click shows the file's diff in the preview, in Review's diff view),
// Commit of the files the person ticks, Switch branch, Pull (fast-forward only) and Push (on the press only). A pull or
// a push runs on the host, off its thread: it shows as busy (git.status says `running`, then the outcome as `last`) and
// the rest of the page stays usable. A folder with no git (projects.list `git: false`) is offered Start git here.
import { useEffect, useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { html, cls } from "../html.js";
import { command, toast } from "../link.js";
import { ask } from "../board/store.js";
import { preview, showGitDiff, showFile } from "./store.js";
import { File } from "./diffview.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { currentProject, startGit } from "./projects.js";

export const gitStatus = signal(null);      // git.status, or {nogit: true} for a folder with no git
const BUSY = signal("");                    // "pull" | "push" | "commit" | ""

export async function loadStatus() {
  try {
    const got = await command("git.status");
    gitStatus.value = got || null;
  } catch { gitStatus.value = { nogit: true }; }
}

export function resetGit() { gitStatus.value = null; }

const STATUS_WORDS = { modified: "modified", added: "added", deleted: "deleted", renamed: "renamed", untracked: "new", conflicted: "conflict" };

function aheadWords(s) {
  if (!s.upstream) return "no upstream";
  const bits = [s.ahead ? `${s.ahead} ahead` : "", s.behind ? `${s.behind} behind` : ""].filter(Boolean);
  return bits.length ? `${bits.join(" · ")} of ${s.upstream}` : `in step with ${s.upstream}`;
}

export function SwitchDialog({ branch, work }) {
  const [list, setList] = useState(null);
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    command("git.branches").then((got) => setList(got?.branches || []))
      .catch((err) => { setList([]); setWhy(err.message || ""); });
  }, []);
  const go = async (to) => {
    if (busy) return;
    setBusy(true);
    setWhy("");
    try {
      const got = await command("git.switch", { branch: to });
      if (got?.error) { setWhy(got.error); return; }
      await loadStatus();
      closeDialog();
    } catch (err) { setWhy(err.message || ""); } finally { setBusy(false); }
  };
  return html`<${Modal} title="Switch branch" onClose=${closeDialog}
    foot=${html`<button type="button" class="ok-btn" onClick=${closeDialog}>Cancel</button>`}>
    <div class="shell-form">
      <p>You are on <code>${branch || "no branch"}</code>.</p>
      ${list === null ? html`<p class="ok-tone-muted">Reading the branches…</p>`
        : list.length === 0 ? html`<p class="ok-tone-muted">This repository has no branch yet.</p>`
        : html`<div class="shell-menu__list" role="list" aria-label="Branches">${list.map((b) => html`<button type="button" key=${b.name} role="listitem"
          class=${cls("shell-menu__item", { "is-on": b.current })} disabled=${b.current || busy} aria-current=${b.current ? "true" : undefined}
          onClick=${() => go(b.name)}><code>${b.name}</code>${b.name === work ? html` <span class="ok-tone-muted">the work branch</span>` : ""}${b.current ? html` <span class="ok-tone-muted">you are here</span>` : ""}${b.upstream ? html` <span class="ok-tone-muted">· ${b.upstream}</span>` : ""}</button>`)}</div>`}
      ${why && html`<p class="ok-tone-error" role="alert">${why}</p>`}
      <p class="ok-font-status ok-tone-muted">Refused while files have uncommitted changes: commit them first.</p>
    </div>
  <//>`;
}

export function GitSection() {
  const s = gitStatus.value;
  const [picked, setPicked] = useState(new Set());
  const [message, setMessage] = useState("");
  const [why, setWhy] = useState("");
  const noGit = currentProject.value?.git === false;     // projects.list says so: git.status is not asked
  const busy = BUSY.value || s?.running || "";
  useEffect(() => {
    if (noGit) { resetGit(); return undefined; }
    loadStatus();
    let n = 0;
    const id = setInterval(() => {       // a pull or a push runs on the host: asked every second until it is done
      n += 1;
      if (gitStatus.value?.running || (n % 5 === 0 && !BUSY.value)) loadStatus();
    }, 1000);
    return () => clearInterval(id);
  }, [noGit]);
  const files = s?.files || [];
  const tick = files.filter((f) => picked.has(f.path)).map((f) => f.path);   // only what is still changed
  const run = async (op) => {
    BUSY.value = op;
    setWhy("");
    try {
      const got = await command(`git.${op}`);
      if (got?.error) setWhy(got.error);
    } catch (e) { setWhy(e.message || ""); } finally { BUSY.value = ""; }
    await loadStatus();
  };
  const commit = async (e) => {
    e?.preventDefault();
    if (!tick.length || !message.trim() || busy) return;
    BUSY.value = "commit";
    setWhy("");
    try {
      const got = await command("git.commit", { paths: tick, message: message.trim(), device: "desktop" });
      if (got?.error) setWhy(got.error);
      else { setMessage(""); setPicked(new Set()); toast(`Committed ${tick.length} file${tick.length === 1 ? "" : "s"} (${got.commit})`, "information", "Commit"); }
    } catch (err) { setWhy(err.message || ""); } finally { BUSY.value = ""; }
    await loadStatus();
  };
  if (!noGit && !s) return html`<section class="shell-git" aria-label="Git"><h3 class="board-sub">Git</h3><p class="ok-tone-muted">Reading git…</p></section>`;
  if (noGit || s.nogit) {
    return html`<section class="shell-git" aria-label="Git"><h3 class="board-sub">Git</h3>
      <p class="ok-tone-muted">This folder has no git.</p>
      <p><button class="ok-btn" onClick=${async () => { if (await startGit(currentProject.value?.path)) resetGit(); }}>Start git here</button></p>
      <p class="ok-font-status ok-tone-muted">Makes a first commit of the folder's files as they are.</p></section>`;
  }
  const isWork = s.work_branch && s.branch === s.work_branch;
  const where = isWork ? "work branch" : s.branch === "main" ? "main" : "";
  const shown = preview.value?.kind === "gitdiff" ? preview.value.path : "";
  return html`<section class="shell-git" aria-label="Git"><h3 class="board-sub">Git</h3>
    <div class="shell-git__branch"><b data-git="branch">${s.branch || "no branch"}</b>${where && html` <span class="shell-chip__tag">${where}</span>`}
      <span class="ok-font-status ok-tone-muted" data-git="ahead">${aheadWords(s)}</span>
      <button class="shell-quiet" onClick=${() => openDialog("switch-branch", { branch: s.branch, work: s.work_branch })}>Switch branch</button></div>
    ${files.length === 0 ? html`<p class="ok-tone-muted" data-git="clean">No changes.</p>` : html`<ul class="shell-git__files" aria-label="Changed files">${files.map((f) => html`<li key=${f.path}
      class=${cls("shell-git__file", { "is-on": f.path === shown })}>
      <label class="shell-git__tick"><input type="checkbox" aria-label=${`Commit ${f.path}`} checked=${picked.has(f.path)}
        onChange=${(e) => { const n = new Set(picked); e.target.checked ? n.add(f.path) : n.delete(f.path); setPicked(n); }} /></label>
      <button class="shell-git__name" title=${f.path} onClick=${() => showGitDiff(f.path)}>${f.path}</button>
      <span class="shell-git__st ok-tone-muted">${STATUS_WORDS[f.status] || f.status}</span>
      <span class="shell-file__n"><span class="is-add">+${f.added}</span> <span class="is-del">−${f.removed}</span></span></li>`)}</ul>`}
    ${files.length > 0 && html`<form class="shell-git__commit" onSubmit=${commit}>
      <input class="ok-input" aria-label="Commit message" placeholder="What changed" value=${message} onInput=${(e) => setMessage(e.target.value)} />
      <button type="submit" class="ok-btn primary" disabled=${!tick.length || !message.trim() || !!busy}>Commit${tick.length ? ` ${tick.length} file${tick.length === 1 ? "" : "s"}` : ""}</button></form>`}
    ${why && html`<p class="ok-tone-error" role="alert">${why}</p>`}
    ${s.last && html`<p class=${cls("ok-font-status", s.last.ok ? "ok-tone-muted" : "ok-tone-error")} data-git="last" role=${s.last.ok ? "status" : "alert"}>${s.last.said}</p>`}
    <div class="shell-git__sync">
      <button class="ok-btn" disabled=${!!busy} aria-busy=${busy === "pull"} title="Brings in what origin has, when it fast-forwards" onClick=${() => run("pull")}>${busy === "pull" ? "Pulling…" : "Pull"}</button>
      <button class="ok-btn" disabled=${!!busy} aria-busy=${busy === "push"} title="Sends your code to origin" onClick=${() => run("push")}>${busy === "push" ? "Pushing…" : "Push"}</button>
      <button class="shell-quiet" onClick=${loadStatus}>Refresh</button></div>
    <p class="ok-font-status ok-tone-muted">Push sends your code to origin, only when you press it. Pull only fast-forwards.</p>
  </section>`;
}

/** A changed file's diff in the preview, as Review shows a result's code. */
export function GitDiffView({ path }) {
  const [d, setD] = useState(null);
  const [gone, setGone] = useState(false);
  useEffect(() => {
    setD(null); setGone(false);
    ask("git.diff", { path }).then((got) => { if (got) setD(got); else setGone(true); });
  }, [path]);
  return html`<div class="shell-gitdiff">
    <p><button class="board-link" onClick=${() => showFile(path)}>Open the file</button></p>
    ${gone ? html`<p class="ok-tone-muted">That file has no changes to show.</p>`
      : !d ? html`<p class="ok-tone-muted">Reading the changes…</p>`
      : html`<p class="ok-font-status ok-tone-muted">Against the last commit${d.branch ? ` on ${d.branch}` : ""}.</p>
        ${d.files.map((f) => html`<${File} key=${f.path} f=${f} open=${true} />`)}
        ${d.truncated && html`<p class="ok-tone-muted">This file is too large to show.</p>`}`}
  </div>`;
}
