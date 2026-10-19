// orkUI's marks on the page (design-system/orkui, served at /ds/orkui/; docs/specs/40-design-system.md): its pixel icons and
// its chevrons, never a typed glyph; and the races' heads, who does a task (decisions §53): an agent's craft is its race (an ork
// engineers, an elf designs, a goblin minds the data, a gnome markets), the gear on its head its tier (a novice bare, a
// seasoned in iron, a veteran hooded). A head never stands alone: its words are beside it or in its title.
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

/** A race's head (orkUI races/), pixelated: 24 x 22 (its @2x for a sharp screen), or `small` 12 x 11, a pixel a cell, an accent in a
 *  line of text. A head is an accent, never a picture to look at: the smallest that says it. Its word goes beside it. */
export function Head({ race, tier = "laborer", small = false, title = "" }) {
  const src = `${ORKUI}/races/${race}-${tier}`;
  return html`<img class=${`ork-race__head${small ? " small" : ""}`} src=${`${src}.png`} srcset=${small ? undefined : `${src}@2x.png 2x`}
    width=${small ? 12 : 24} height=${small ? 11 : 22} alt="" title=${title || undefined} draggable="false" />`;
}

/** The tabs' marks, orkUI's pixel icons: the Board a list, Agents a robot (a head says a craft, not every agent), Review an eye. */
export function TabMark({ tab }) {
  return html`<${Icon} name=${{ board: "list-box", agents: "robot" }[tab] || "eye"} />`;
}

/** What needs the person, by kind, as orkUI's icon (Needs you, desktop and phone alike). */
export const NEED_ICONS = { goal: "flag", asks: "warning-diamond", plan: "list-box", todo: "checkbox", failed: "square-alert", proposal: "lightbulb",
  op: "checkbox", op_failed: "square-alert", op_rules: "sliders" };

// The words of a head, as realm/lexicon.py says them (tier.*, race.*, craft.*; tests/test_design_system.py keeps them so).
export const TIER_WORDS = { elder: "Veteran", warrior: "Seasoned", laborer: "Novice" };
export const RACE_WORDS = { peon: "ork", elf: "elf", goblin: "goblin", gnome: "gnome", lich: "lich" };
export const CRAFT_WORDS = { engineering: "Engineering", design: "Design", data: "Data", marketing: "Marketing", product: "Product" };

/** "Seasoned elf · Design": what a head says, in words. */
export const headWords = (head) => (head ? `${TIER_WORDS[head.tier] || ""} ${RACE_WORDS[head.race] || ""} · ${CRAFT_WORDS[head.craft] || ""}` : "");

/** Who does it (`head`: {craft, race, tier} as the host sends it, realm/roles.py `head`), its words in its title; `small` in a line. */
export function WhoHead({ head, small = false }) {
  return head ? html`<${Head} race=${head.race} tier=${head.tier} small=${small} title=${headWords(head)} />` : null;
}

/** A head beside its words: the tier, then the race and the craft, muted (orkUI's .ork-race). */
export function Who({ head, small = false }) {
  if (!head) return null;
  return html`<span class=${`ork-race${small ? " small" : ""}`} data-race=${head.race} data-tier=${head.tier}><${Head} race=${head.race} tier=${head.tier} small=${small} />
    <span class="ork-race__word">${TIER_WORDS[head.tier]} <span class="ork-race__tier">${RACE_WORDS[head.race]} · ${CRAFT_WORDS[head.craft]}</span></span></span>`;
}
