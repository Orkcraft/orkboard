// Every line of the page can be taken away, an error with the day's logs (the owner's notes of 19 October):
// - an error line says its words with Copy and Save logs (`ErrorLine`), as an error toast does;
// - Save logs writes the day's logs to the Downloads folder (gui/logs_save.py: the app's window downloads nothing a
//   link gives it) with what was on the screen, and says where, with Show;
// - in the app's window, whose web view has no menu of its own, a right click on any line opens Copy (the selection,
//   else that line) and, on an error, Save logs with it (`ContextMenu`); a browser keeps its own menu.
import { signal } from "@preact/signals";
import { html } from "../html.js";
import { command, copyText, toast } from "../link.js";
import { SignInButton, entryFor } from "./signin.js";

const CHARS = 20000;
const LINE = "p, li, td, th, dt, dd, h1, h2, h3, h4, label, button, a, pre, code, summary, [role=alert], [role=status], .ok-toast";
const ERROR = "[role=alert], .ok-tone-error, .ok-toast.is-error, .warn";

/** The day's logs (or the last `days`) saved with `said`, the words on the screen; then where, with Show. */
export async function saveLogs(said = "", days = 1) {
  let got;
  try { got = await command("logs.save", { said: String(said || "").slice(0, CHARS), days }); } catch { got = null; }
  if (!got || got.error) { toast(got?.error || "The logs could not be saved", "error"); return null; }
  toast(`Logs saved: ${got.path}`, "information", "", 12, null, [
    { label: "Show", run: () => command("logs.show", { path: got.path }).then((r) => r?.error && toast(r.error, "error")).catch(() => {}) },
    { label: "Copy path", run: () => copyText(got.path) }]);
  return got;
}

/** An error in words, with Copy and Save logs beside it (the words go into the logs saved). */
export function ErrorLine({ text, logs = true }) {
  if (!text) return null;
  const tool = entryFor(text);       // a tool that is not signed in (spec 45 §8): Sign in beside its line
  return html`<div class="shell-error"><p class="ok-tone-error" role="alert">${text}</p>
    <span class="shell-error__acts">${tool && html`<${SignInButton} harness=${tool.harness} tool=${tool.tool} />`}<button type="button" class="ork-btn quiet" onClick=${() => { copyText(text); toast("Copied", "information"); }}>Copy</button>
      ${logs && html`<button type="button" class="ork-btn quiet" onClick=${() => saveLogs(text)}>Save logs</button>`}</span></div>`;
}

/** The app's window (gui/board_host.py `show` opens it with `app=1`): a browser keeps its own menu. */
export const inWindow = () => new URLSearchParams(location.search).get("app") === "1";

const menu = signal(null);                     // {x, y, text, error}

/** The words a right click means: the selection, else the line under the pointer. */
export function lineAt(el) {
  const sel = window.getSelection ? window.getSelection().toString() : "";
  if (sel.trim()) return sel.trim().slice(0, CHARS);
  const line = el?.closest?.(LINE) || el;
  return String(line?.innerText || line?.textContent || "").trim().slice(0, CHARS);
}

export function onContextMenu(e) {
  if (!inWindow()) return;
  const el = e.target;
  if (el?.closest?.("input, textarea, select, [contenteditable=true], .xterm")) return;   // their own copy and paste
  const text = lineAt(el);
  if (!text) return;
  e.preventDefault();
  const err = el.closest(ERROR);
  menu.value = { x: e.clientX, y: e.clientY, text, error: err ? String(err.innerText || "").trim().slice(0, CHARS) : "" };
}

const close = () => { menu.value = null; };

export function ContextMenu() {
  const m = menu.value;
  if (!m) return null;
  const run = (fn) => () => { close(); fn(); };
  const x = Math.min(m.x, window.innerWidth - 240), y = Math.min(m.y, window.innerHeight - 96);
  return html`<div class="shell-ctx" onClick=${close} onContextMenu=${(e) => { e.preventDefault(); close(); }}>
    <div class="ork-menu shell-ctx__menu" role="menu" aria-label="Copy" style=${`left:${Math.max(0, x)}px;top:${Math.max(0, y)}px`}
      onClick=${(e) => e.stopPropagation()}>
      <button role="menuitem" class="ork-menu__item" data-k="c" autofocus onClick=${run(() => { copyText(m.text); toast("Copied", "information"); })}>Copy</button>
      ${m.error && html`<button role="menuitem" class="ork-menu__item" data-k="l" onClick=${run(() => saveLogs(m.error))}>Save logs with it</button>`}
    </div></div>`;
}

window.addEventListener("keydown", (e) => {            // the menu's Esc closes the menu, never a tab under it
  if (e.key === "Escape" && menu.value) { e.stopPropagation(); close(); }
}, true);
window.addEventListener("blur", close);
