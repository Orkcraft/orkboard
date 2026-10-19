// orkUI's marks on the page (design-system/orkui, served at /ds/orkui/; docs/specs/40-design-system.md): its pixel icons and
// its chevrons, never a typed glyph.
import { html } from "./html.js";

export const ORKUI = "/ds/orkui";

/** One of orkUI's pixel icons (icons/icons.svg: flag, robot, eye, sliders, close, …), 24 px, in the text's colour. */
export function Icon({ name, label = "" }) {
  return html`<svg class="ork-icon" aria-hidden=${label ? undefined : "true"} role=${label ? "img" : undefined} aria-label=${label || undefined}>
    <use href=${`${ORKUI}/icons/icons.svg#${name}`} /></svg>`;
}

/** orkUI's chevron: down (a menu, an open fold), up, right (a closed fold) or left. */
export function Chev({ dir = "down" }) {
  return html`<i class=${`ork-chev${dir === "down" ? "" : ` ${dir}`}`} aria-hidden="true"></i>`;
}

/** A race's head (orkUI races/: 24 x 22, its @2x for a sharp screen), pixelated; `big` 48 x 44. Its word goes beside it. */
export function Head({ race, tier = "laborer", big = false, title = "" }) {
  const src = `${ORKUI}/races/${race}-${tier}`;
  return html`<img class="ork-race__head" src=${`${src}${big ? "@2x" : ""}.png`} srcset=${big ? undefined : `${src}@2x.png 2x`}
    width=${big ? 48 : 24} height=${big ? 44 : 22} alt="" title=${title || undefined} draggable="false" />`;
}

/** The tabs' marks: the Board a list, Agents an ork (the mascot, orkUI's peon), Review an eye. */
export function TabMark({ tab }) {
  return tab === "agents" ? html`<${Head} race="peon" />` : html`<${Icon} name=${tab === "board" ? "list-box" : "eye"} />`;
}

/** What needs the person, by kind, as orkUI's icon (Needs you, desktop and phone alike). */
export const NEED_ICONS = { goal: "flag", asks: "warning-diamond", plan: "list-box", todo: "checkbox", failed: "square-alert", proposal: "lightbulb",
  op: "checkbox", op_failed: "square-alert", op_rules: "sliders" };
