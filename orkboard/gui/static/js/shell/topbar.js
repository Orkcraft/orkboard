// The top bar (docs/specs/33-v1-shell.md §6, spec 49 §3): the project switcher · Orkline · the Target · Agents and Files (the drawer's
// panes) · today's Spend · Stop all · the gear. What is left of each AI tool is at the bottom right of the window (arena/limits.js).
// Roles only: warning at 20 % or less left, danger at 5 % or less (docs/design-system.md).
import { html } from "../html.js";
import { Icon } from "../orkui.js";
import { town, command, say } from "../link.js";
import { TargetChip } from "../board/target.js";
import { showAgents, showFiles } from "./store.js";
import { openDialog } from "./modals.js";
import { ProjectSwitcher, currentProject, projectsOn } from "./projects.js";

export const WARN = 0.2, DANGER = 0.05;

export const levelOf = (left) => (left <= DANGER ? "danger" : left <= WARN ? "warn" : "ok");

/** "resets at 18:00", or with the day when it is not today. */
export function resetWords(iso, now = new Date()) {
  const d = new Date(iso);
  if (!iso || Number.isNaN(d.getTime())) return "";
  const hm = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  return d.toDateString() === now.toDateString() ? `resets at ${hm}` : `resets ${d.toLocaleDateString([], { weekday: "short" })} ${hm}`;
}

function Gear() {
  return html`<button class="ork-btn" aria-label="Settings" aria-haspopup="dialog" onClick=${() => openDialog("settings")}><${Icon} name="sliders" /></button>`;
}

export function TopBar() {
  const hud = town.value?.hud || {};
  const spend = hud.show_gold ? hud.gold : hud.lumber;
  const shown = !projectsOn.value || !!currentProject.value?.path;      // the window is behind the project: the start screen has no drawer
  return html`<header class="shell-top">
    <${ProjectSwitcher} />
    <span class="shell-top__brand">Orkline</span>
    ${shown && html`<${TargetChip} />`}
    <span class="shell-top__spacer"></span>
    ${shown && html`<button type="button" class="ork-btn" title="The agents, what each takes and is doing" onClick=${() => showAgents()}>Agents</button>`}
    ${shown && projectsOn.value && html`<button type="button" class="ork-btn" title="The project’s files" onClick=${() => showFiles()}>Files</button>`}
    <button type="button" class="shell-top__spend" title="What was spent today. This week's work" aria-haspopup="dialog"
      aria-label=${`Spend today: ${spend ?? "—"}. This week's work`} onClick=${() => openDialog("this_week")}><span class="ok-tone-muted">Spend</span> <b>${spend ?? "—"}</b></button>
    <button class="ork-btn danger" title=${say("Stop every ork, script and browser at once")}
      onClick=${() => command("halt").catch(() => {})}>Stop all</button>
    <${Gear} />
  </header>`;
}
