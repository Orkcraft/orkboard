// Orkboard's page (docs/specs/37-board-and-line.md §4): the v1 shell — Board, Review, the preview and Agents — the
// onboarding's first screen (trust, the AI tools found) and the toasts, in Office's calm look, and no camp module.
// gui/server.py serves it as the page's script when its host is Orkboard (gui/board_host.py); Orkline's page is
// app.js, which draws the same shell when `focus` is "board".
import { render } from "preact";
import { html, cls, linked } from "./js/html.js";
import { town, connect, openLink, copyText, toasts, dismiss, holdToast } from "./js/link.js";
import { Onboarding } from "./js/onboarding.js";
import { ContextMenu, onContextMenu, saveLogs } from "./js/shell/errors.js";
import { watchErrors } from "./js/crashes.js";
import { Shell } from "./js/shell/shell.js";

const SEVERITY = { warning: "is-warn", error: "is-error", information: "is-ok" };
const MARK = { information: "✓", warning: "⚠", error: "✗" };

/** The toasts as Orkline's (js/chrome.js `Toasts`), without its tool-failure card: Orkboard reports no tool failure
 *  through the town's Switch and Retry (gui/failures.py). */
function Toasts() {
  return html`<div class="gui-toasts" role="status" aria-live="polite">
    ${toasts.value.map((x) => html`<div key=${x.id} data-toast=${x.id}
        class=${cls("ok-toast gui-toast kit-frame-thin kit-paper", { [SEVERITY[x.severity] || "is-ok"]: true })}
        onMouseEnter=${() => holdToast(x.id, true)} onMouseLeave=${() => holdToast(x.id, false)}>
      <span class="ok-toast__mark">${MARK[x.severity] || "✓"}</span>
      <span class="gui-toast__text">${x.title ? html`<b>${x.title}</b> — ` : ""}${linked(x.message)}</span>
      <span class="gui-toast__acts">
        ${(x.acts || []).map((a) => html`<button key=${a.label} class="ork-btn quiet" onClick=${() => { dismiss(x.id); a.run(); }}>${a.label}</button>`)}
        ${x.severity === "error" && html`<button class="ork-btn quiet" onClick=${() => { dismiss(x.id); saveLogs(`${x.title ? x.title + " — " : ""}${x.message}`); }}>Save logs</button>`}
        <button class="gui-toolerr__close" title="Copy" aria-label="Copy" onClick=${() => copyText(`${x.title ? x.title + " — " : ""}${x.message}`)}>⧉</button>
        <button class="gui-toolerr__close" title="Close" aria-label="Close" onClick=${() => dismiss(x.id)}>×</button></span>
    </div>`)}
  </div>`;
}

function Board() {
  const t = town.value;
  if (!t) return html`<div class="gui-loading ok-font-body">Opening the board…</div>`;
  return html`<div class="gui gui-board">${t.onboarding ? html`<${Onboarding} />` : html`<${Shell} />`}<${Toasts} /><${ContextMenu} /></div>`;
}

// A link to another site opens in the browser, never in the app's own window.
document.addEventListener("click", (e) => {
  const a = e.target instanceof Element && e.target.closest("a[href]");
  if (!a || e.defaultPrevented || !/^https?:/i.test(a.href) || new URL(a.href).origin === location.origin) return;
  e.preventDefault();
  openLink(a.href);
});

document.documentElement.dataset.look = "office";
document.documentElement.dataset.theme = "office";
watchErrors();
connect();
render(html`<${Board} />`, document.getElementById("app"));

// A right click in the app's window: Copy that line, Save logs with an error (js/shell/errors.js).
document.addEventListener("contextmenu", onContextMenu);

// Copy in a window whose shell has no Edit menu (a webview): Ctrl/⌘ + C puts the selected text on the clipboard itself.
window.addEventListener("keydown", (e) => {
  if (!(e.ctrlKey || e.metaKey) || e.shiftKey || e.altKey || (e.key !== "c" && e.key !== "C")) return;
  const on = document.activeElement;
  if (on && (on.tagName === "INPUT" || on.tagName === "TEXTAREA")) return;
  const text = window.getSelection ? window.getSelection().toString() : "";
  if (text) copyText(text);
});
