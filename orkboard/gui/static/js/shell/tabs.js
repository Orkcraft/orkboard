// The drawer's tab strip (docs/specs/39-map.md §3, spec 49 §9): a tab per thing opened, none pinned. The passing tab is in italics;
// a double-click or Keep keeps it. × or a middle click closes a tab; *Close the drawer* (×) at the right puts the drawer away and keeps
// its tabs. A `tablist`: the arrow keys move between the tabs, Enter shows one.
import { html, cls } from "../html.js";
import { Icon } from "../orkui.js";
import { tabs, active, editing, activate, closeTab, keepTab, hideDrawer, kindWords } from "./store.js";

const NAMES = { gate: "dev → main", agents: "Agents", files: "Files" };
const fallback = (p) => NAMES[p.kind] || p.path || p.slug || "…";

export function TabStrip() {
  const list = tabs.value, now = active.value, dirty = !!editing.value?.dirty;
  const move = (e) => {
    const all = [...e.currentTarget.querySelectorAll("[role=tab]")], at = all.indexOf(document.activeElement);
    const to = e.key === "ArrowRight" ? at + 1 : e.key === "ArrowLeft" ? at - 1 : e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : null;
    if (at < 0 || to === null) return;
    e.preventDefault();
    all[(to + all.length) % all.length].focus();
  };
  return html`<header class="shell-tabstrip" role="presentation">
    <div class="shell-tabstrip__tabs" role="tablist" aria-label="Opened" onKeyDown=${move}>
    ${list.map((t) => {
      const on = now === t.id, label = kindWords(t.p.kind), title = t.title || fallback(t.p);
      return html`<span key=${t.id} class=${cls("shell-ptab", { "is-on": on, "is-passing": !t.kept })} data-tab=${t.id}>
        <button role="tab" class="shell-ptab__main" aria-selected=${on} tabindex=${on ? 0 : -1} title=${`${label}: ${title}`}
          onClick=${() => activate(t.id)} onDblClick=${() => keepTab(t.id)}
          onMouseDown=${(e) => { if (e.button === 1) e.preventDefault(); }}
          onAuxClick=${(e) => { if (e.button === 1) { e.preventDefault(); closeTab(t.id); } }}>
          <span class="shell-ptab__kind">${label}</span> <span class="shell-ptab__title">${title}</span>${on && dirty ? html`<span class="shell-ptab__dirty" aria-label="Unsaved changes"> ●</span>` : ""}</button>
        ${on && !t.kept && html`<button class="shell-ptab__keep" aria-label=${`Keep ${title}`} title="Keep this tab: a click elsewhere will not replace it" onClick=${() => keepTab(t.id)}>Keep</button>`}
        <button class="shell-ptab__x" aria-label=${`Close ${title}`} title="Close this tab" onClick=${() => closeTab(t.id)}>×</button></span>`;
    })}
    </div>
    <button class="shell-drawer__x" aria-label="Close the drawer" title="Close the drawer (Esc)" onClick=${hideDrawer}><${Icon} name="close" /></button>
  </header>`;
}
