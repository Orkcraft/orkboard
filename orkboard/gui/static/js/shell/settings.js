// The gear's menu (docs/specs/33-v1-shell.md §4, §9; spec 34 §5–§6), in the shell's modal: Push after merging, Download
// today's logs, Pair a phone. The theme follows the system.
import { html } from "../html.js";
import { review, act } from "./store.js";
import { board } from "../board/store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { currentProject } from "./projects.js";

/** The analytics zip of the last `days` days (gui/server.py `/api/analytics`): the model calls, the event log, each idea's plan and logs. */
const logsHref = (days) => `/api/analytics?days=${days}&t=${encodeURIComponent(new URLSearchParams(location.search).get("t") || "")}`;

/** "01:00-07:00" → ["01:00", "07:00"]. */
const window_ = (night) => (/^\d\d:\d\d-\d\d:\d\d$/.test(night || "") ? night.split("-") : ["01:00", "07:00"]);

export function SettingsDialog() {
  const push = !!review.value?.push;
  const b = board.value;
  const [from, to] = window_(b?.night);
  return html`<${Modal} title="Settings" onClose=${closeDialog} foot=${html`<button type="button" class="ok-btn primary" onClick=${closeDialog}>Done</button>`}>
    <div class="shell-form">
      ${currentProject.value && html`<p class="ok-font-status ok-tone-muted" data-settings="project">The Board's settings are for this project: ${currentProject.value.name}.</p>`}
      <label class="ok-check">
        <input type="checkbox" class="gui-onb__hide" checked=${push} onChange=${(e) => act("ideas.into", { push: e.target.checked })} />
        <i>${push ? "✓" : ""}</i><span>Push after merging (sends your code to origin)</span></label>
      ${b && html`<div class="shell-field" role="group" aria-label="The Board">
        <label class="ok-check">
          <input type="checkbox" class="gui-onb__hide" checked=${!!b.autostart} onChange=${(e) => act("ideas.board_set", { autostart: e.target.checked })} />
          <i>${b.autostart ? "✓" : ""}</i><span>Start plans by themselves</span></label>
        <span class="ok-font-status ok-tone-muted">Low-risk plans start alone; the rest wait for you.</span>
        <div class="board-row"><span class="ok-font-label">Night</span>
          <input class="ok-input" type="time" value=${from} aria-label="Night from" onChange=${(e) => e.target.value && act("ideas.board_set", { night: `${e.target.value}-${to}` })} />
          <span aria-hidden="true">–</span>
          <input class="ok-input" type="time" value=${to} aria-label="Night to" onChange=${(e) => e.target.value && act("ideas.board_set", { night: `${from}-${e.target.value}` })} /></div>
        <span class="ok-font-status ok-tone-muted">The low work, the refresh and the proposals wait for the night (your machine's time).</span></div>`}
      <div class="shell-field"><span class="ok-font-label">Your phone</span>
        <span><button type="button" class="ok-btn" onClick=${() => openDialog("pair")}>Pair a phone</button></span></div>
      <div class="shell-gear__logs"><span class="ok-font-label">Download today's logs</span>
        <a class="ok-btn" href=${logsHref(1)} download>Today</a><a class="ok-btn" href=${logsHref(7)} download>The last 7 days</a></div>
      <p class="ok-font-status ok-tone-muted">What you did and what the orks did, on this machine only. Off by default. The colours follow your system's light or dark setting.</p>
    </div>
  <//>`;
}
