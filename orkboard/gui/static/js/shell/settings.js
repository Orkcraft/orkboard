// The gear's menu (docs/specs/33-v1-shell.md §4, §9; spec 34 §5–§6), in the shell's modal: Push after merging, Download
// today's logs, Pair a phone, Keep the computer awake (spec 47 §5). The theme follows the system.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { command } from "../link.js";
import { review, act } from "./store.js";
import { board } from "../board/store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { currentProject } from "./projects.js";
import { saveLogs } from "./errors.js";


/** "01:00-07:00" → ["01:00", "07:00"]. */
const window_ = (night) => (/^\d\d:\d\d-\d\d:\d\d$/.test(night || "") ? night.split("-") : ["01:00", "07:00"]);

const AWAKE_MODES = [["off", "Never"], ["carts", "While the orks work"], ["phone", "Stay reachable from your phone"]];
const AWAKE_LINES = {
  off: "The computer sleeps as its power settings say. While it sleeps the orks stop, the night's work waits, and a phone cannot reach it.",
  carts: "On power, it does not sleep by itself while an ork or an operation is at work, or while the Board has work waiting for tonight. "
    + "With nothing to do, or on battery, it sleeps as its power settings say.",
  phone: "On power, it does not sleep by itself while Orkline is open and a phone is paired, work or not. "
    + "On battery it sleeps as its power settings say, and the phone says so.",
};
const AWAKE_NOW = { work: "Holding now: an ork is at work.", tonight: "Holding now: the Board has work for tonight.", phone: "Holding now: a phone is paired." };

/** The lines under the three choices, from `awake.state` (gui/keep_awake.py `state`). */
export function awakeLines(a) {
  if (a.mode === "off") return [AWAKE_LINES.off];
  if (!a.can) return ["This computer gives Orkline no way to keep it awake: set its power settings so it does not sleep while the orks work."];
  const now = a.battery ? "On battery now, so it may sleep." : AWAKE_NOW[a.why] || "Not holding now: nothing to do.";
  return [AWAKE_LINES[a.mode] || AWAKE_LINES.carts, ...(a.mode === "phone" && !a.paired ? ["No phone is paired yet: Pair a phone, above."] : []),
    now, "The screen still turns off. A laptop with its lid closed still sleeps unless a display is attached."];
}

/** Keep the computer awake: Never · While the orks work · Stay reachable from your phone, read when the dialog opens and every 30 s. */
function AwakeField() {
  const [a, setA] = useState(null);
  useEffect(() => {
    const read = () => command("awake.state").then(setA, () => {});
    read();
    const t = setInterval(read, 30000);
    return () => clearInterval(t);
  }, []);
  if (!a) return null;
  const pick = (mode) => { setA({ ...a, mode }); command("awake.set", { mode }).then(setA, () => {}); };
  return html`<div class="shell-field" role="group" aria-label="Keep the computer awake" data-settings="awake"><span class="ok-font-label">Keep the computer awake</span>
    <div class="shell-seg">${AWAKE_MODES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${a.mode === id ? " is-on" : ""}`}>
      <input type="radio" name="awake" class="gui-onb__hide" checked=${a.mode === id} onChange=${() => pick(id)} />${name}</label>`)}</div>
    ${awakeLines(a).map((l, n) => html`<span key=${n} class="ok-font-status ok-tone-muted">${l}</span>`)}</div>`;
}

export function SettingsDialog() {
  const push = !!review.value?.push;
  const b = board.value;
  const [from, to] = window_(b?.night);
  return html`<${Modal} title="Settings" onClose=${closeDialog} foot=${html`<button type="button" class="ork-btn primary" onClick=${closeDialog}>Done</button>`}>
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
          <input class="ork-field" type="time" value=${from} aria-label="Night from" onChange=${(e) => e.target.value && act("ideas.board_set", { night: `${e.target.value}-${to}` })} />
          <span aria-hidden="true">–</span>
          <input class="ork-field" type="time" value=${to} aria-label="Night to" onChange=${(e) => e.target.value && act("ideas.board_set", { night: `${from}-${e.target.value}` })} /></div>
        <span class="ok-font-status ok-tone-muted">The low work, the refresh and the proposals wait for the night (your machine's time).</span></div>`}
      <div class="shell-field"><span class="ok-font-label">Your phone</span>
        <span><button type="button" class="ork-btn" onClick=${() => openDialog("pair")}>Pair a phone</button></span></div>
      <${AwakeField} />
      <div class="shell-gear__logs"><span class="ok-font-label">Download today's logs</span>
        <button type="button" class="ork-btn" onClick=${() => saveLogs("", 1)}>Today</button>
        <button type="button" class="ork-btn" onClick=${() => saveLogs("", 7)}>The last 7 days</button></div>
      <p class="ok-font-status ok-tone-muted">Saved in your Downloads folder: every model call with what went in and came out, and where Orkline runs.</p>
      <p class="ok-font-status ok-tone-muted">What you did and what the orks did, on this machine only. Off by default. The colours follow your system's light or dark setting.</p>
    </div>
  <//>`;
}
