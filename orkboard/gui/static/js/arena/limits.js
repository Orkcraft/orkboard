// What is left of your AI tools (docs/specs/49-one-window.md §8): at the bottom right, a line per tool of the snapshot's limits — its
// mark and name, ten diamonds for what is left (the last ones hatched for the reserve, Claude only), its % — and under them what the
// hatching is and when the tightest window resets. A tool whose limits were not read says so and has no diamonds.
import { html, cls } from "../html.js";
import { ORKUI } from "../orkui.js";
import { town } from "../link.js";
import { resetWords } from "../shell/topbar.js";
import { limitLine } from "./arenawords.js";

const MARKED = ["claude", "codex", "agy", "cursor", "hermes", "pi"];

export function Limits() {
  const t = town.value, reserve = t?.reserve || null;
  const lines = (t?.limits || []).map((l) => limitLine(l, reserve, resetWords));
  const kept = lines.some((l) => l.kept);
  const reset = lines.find((l) => l.reset)?.reset || "";
  return html`<section class="arena-limits" aria-label="What is left of your AI tools">
    ${lines.map((l) => html`<span key=${l.provider} class=${cls("arena-limit", { "is-unread": !l.read })} data-provider=${l.provider} title=${l.tip} tabindex="0" aria-label=${l.tip}>
      <span class="arena-limit__name">${MARKED.includes(l.provider) && html`<img class="ork-mark" src=${`${ORKUI}/marks/harness-${l.provider}.png`} srcset=${`${ORKUI}/marks/harness-${l.provider}@2x.png 2x`} alt="" draggable="false" />`} ${l.name}</span>
      ${l.read ? html`<span class="ork-crystals" aria-hidden="true">${l.cells.map((c, i) => html`<i key=${i} class=${c}></i>`)}</span><b>${l.pct}</b>` : html`<b class="arena-muted">${l.pct}</b>`}
    </span>`)}
    ${lines.length > 0 && html`<span class="arena-cap arena-limits__note">${kept ? `hatched: kept for ${reserve?.night ? "the morning" : "tonight"}` : ""}${kept && reset ? " · " : ""}${reset}</span>`}
  </section>`;
}
