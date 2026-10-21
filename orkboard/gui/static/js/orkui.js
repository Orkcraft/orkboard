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

/** One of orkUI's signs (signs/<name>.svg, spec 50 §1.6): check, cross, work, night, alert, flag, before, after. Drawn in the colour of the text it
 *  stands in and never alone: its words are beside it or in its `label` (its title). `aria-hidden`. */
export function Sign({ name, big = false, label = "" }) {
  return html`<span class=${`ork-sign ${name}${big ? " big" : ""}`} aria-hidden="true" title=${label || undefined}></span>`;
}

/** A goal's element (orkUI's elements/, spec 50 §1): meadow, ice, dust, void or lava, 14 x 14 (`big` 28 x 28); `dim` while the goal is not
 *  yet read. Shown, never named: `aria-hidden`. A goal the host has not given one yet is drawn dim. */
export function Elem({ name = "", big = false, dim = false }) {
  return html`<span class=${`ork-elem ${name || "dust"}${big ? " big" : ""}${dim || !name ? " dim" : ""}`} aria-hidden="true"></span>`;
}

/** orkUI's chevron: down (a menu, an open fold), up, right (a closed fold) or left. */
export function Chev({ dir = "down" }) {
  return html`<i class=${`ork-chev${dir === "down" ? "" : ` ${dir}`}`} aria-hidden="true"></i>`;
}

/** A race's head (orkUI races/), pixelated: 24 x 22 (its @2x for a sharp screen), `small` 12 x 11, a pixel a cell, an accent in a line of
 *  text, `mid` 36 x 33 (a member's head, from the @2x) or `big` 48 x 44 (the leader's). A head is an accent, never a picture to look at:
 *  the smallest that says it. Its word goes beside it. */
export function Head({ race, tier = "laborer", small = false, size = "", title = "" }) {
  const sz = size || (small ? "small" : ""), src = `${ORKUI}/races/${race}-${tier}`, from2x = sz === "mid" || sz === "big";
  const wide = { small: 12, mid: 36, big: 48 }[sz] || 24, high = { small: 11, mid: 33, big: 44 }[sz] || 22;
  return html`<img class=${`ork-race__head${sz ? ` ${sz}` : ""}`} src=${from2x ? `${src}@2x.png` : `${src}.png`} srcset=${sz || from2x ? undefined : `${src}@2x.png 2x`}
    width=${wide} height=${high} alt="" title=${title || undefined} draggable="false" />`;
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
export function WhoHead({ head, small = false, size = "" }) {
  return head ? html`<${Head} race=${head.race} tier=${head.tier} small=${small} size=${size} title=${headWords(head)} />` : null;
}

/** A head beside its words: the tier, then the race and the craft, muted (orkUI's .ork-race). */
export function Who({ head, small = false }) {
  if (!head) return null;
  return html`<span class=${`ork-race${small ? " small" : ""}`} data-race=${head.race} data-tier=${head.tier}><${Head} race=${head.race} tier=${head.tier} small=${small} />
    <span class="ork-race__word">${TIER_WORDS[head.tier]} <span class="ork-race__tier">${RACE_WORDS[head.race]} · ${CRAFT_WORDS[head.craft]}</span></span></span>`;
}
