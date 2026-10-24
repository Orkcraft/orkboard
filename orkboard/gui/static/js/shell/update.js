// A newer Orkline (gui/updates.py, core/updates.py, docs/updates.md): asked once per version, loudly for a critical
// one, plainly for a major one (a later line, 0.2 → 0.3); one click installs it with the tool that installed this copy,
// and the window opens again on it. "Later" hides an ordinary or a major update until the next version, a critical one
// until the window opens again (under the default policy it installs by itself then). Settings shows it too.
import { signal } from "@preact/signals";
import { html } from "../html.js";
import { command, town } from "../link.js";
import { Modal, dialog, closeDialog } from "./modals.js";

const HIDDEN_KEY = "orkcraft.update.later";
const hidden = signal(readHidden());          // the version "Later" was said to

function readHidden() {
  try { return localStorage.getItem(HIDDEN_KEY) || ""; } catch { return ""; }
}

function later(u) {
  hidden.value = u.version;
  if (u.critical) return;                    // a critical one is asked again when the window opens
  try { localStorage.setItem(HIDDEN_KEY, u.version); } catch { /* the page keeps it for now */ }
}

/** Show the offer again, whatever "Later" said (Settings → Update). */
export const askAgain = () => { hidden.value = ""; };
export const install = () => command("update.install").catch(() => {});
export const checkNow = () => command("update.check").catch(() => {});
export const setPolicy = (policy) => command("update.policy", { policy }).catch(() => {});

/** What the offer is called: a critical one first, then a major one, else a plain newer version. */
export function updateTitle(u) {
  if (u.critical) return `Critical update: Orkline ${u.version}`;
  if (u.major) return `New version: Orkline ${u.version}`;
  return `Orkline ${u.version} is out`;
}

export function UpdateAsk() {
  const t = town.value;
  const u = t && t.update;
  if (!u || !u.version || t.onboarding || dialog.value) return null;
  const busy = u.state === "installing" || u.state === "installed";
  if (!busy && u.state !== "failed" && hidden.value === u.version) return null;
  const notes = (u.critical ? u.critical_notes : u.notes) || [];
  const close = busy ? () => {} : () => later(u);
  const foot = busy
    ? html`<button type="button" class="ork-btn primary" disabled>${u.state === "installed" ? "Restarting…" : "Installing…"}</button>`
    : html`<button type="button" class="ork-btn" onClick=${close}>Later</button>
      ${u.can && html`<button type="button" class="ork-btn primary" data-update="install" onClick=${install}>
        ${u.state === "failed" ? "Try again" : "Update and restart"}</button>`}`;
  return html`<${Modal} title=${updateTitle(u)} onClose=${close} foot=${foot}>
    <div class="shell-form" data-update=${u.critical ? "critical" : u.major ? "major" : "minor"}>
      <p class="ok-font-status ok-tone-muted">You have ${u.current}.</p>
      ${u.critical && !busy && html`<p class="ok-font-status ok-tone-error">It fixes something that can lose work or let harm in: install it now.</p>`}
      ${u.major && !u.critical && !busy && html`<p class="ok-font-status">A major update: what is new may change how you work. Read it before you install.</p>`}
      ${notes.length > 0 && html`<div class="shell-md"><ul>${notes.map((n, k) => html`<li key=${k}>${n}</li>`)}</ul></div>`}
      <p class="ok-font-status ok-tone-muted">${u.can
        ? html`Orkline restarts when it is in: what runs now stops. It installs with <code>${u.how}</code>`
        : html`It cannot install itself here: ${u.how}`}</p>
      ${u.state === "failed" && html`<p class="ok-font-status ok-tone-error">It did not install. Orkline keeps running ${u.current}.</p>
        <pre class="shell-brief">${u.error}</pre>`}
    </div>
  <//>`;
}

const POLICIES = [
  ["critical", "Critical ones", "A critical update (a fix for something that loses work or lets harm in) installs when Orkline opens; the others are offered."],
  ["auto", "All", "Every update installs when Orkline opens."],
  ["ask", "None", "Nothing installs by itself: every update is offered, a critical one loudly."],
];

/** Settings → Updates: the version, what is out with Update, Check now, and which updates install by themselves. */
export function UpdatesField() {
  const t = town.value;
  const u = t && t.update;
  const policy = (u && u.policy) || (t && t.update_policy) || "critical";
  const what = POLICIES.find(([v]) => v === policy) || POLICIES[0];
  return html`<div class="shell-field" role="group" aria-label="Updates" data-settings="updates">
    <span class="ok-font-label">Updates</span>
    ${u && u.version && u.state !== "installed"
      ? html`<div class="board-row"><span class="ok-font-status">${updateTitle(u)} (you have ${u.current}).</span>
          <button type="button" class="ork-btn primary" onClick=${() => { askAgain(); closeDialog(); }}>Update…</button></div>`
      : html`<span class="ok-font-status ok-tone-muted">You have the latest Orkline${t && t.version ? ` (${t.version})` : ""}.</span>`}
    <div class="board-row"><span class="ok-font-label">Install by themselves</span>
      <select class="ork-field" aria-label="Updates that install by themselves" value=${policy} onChange=${(e) => setPolicy(e.target.value)}>
        ${POLICIES.map(([v, label]) => html`<option key=${v} value=${v}>${label}</option>`)}
      </select>
      <button type="button" class="ork-btn" onClick=${checkNow}>Check now</button></div>
    <span class="ok-font-status ok-tone-muted">${what[2]}</span>
  </div>`;
}
