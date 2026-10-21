// orkUI's pixel symbols on the phone (docs/specs/50-parties-and-goals.md §1, §1.6): a goal's element (`.ork-elem`: meadow, ice, dust, void, lava) and the eight signs (`.ork-sign`:
// check, cross, work, night, alert, flag, before, after), drawn as masks of orkUI's own files (elements/, signs/, served beside the sheets: gui/pwa.py). No Unicode symbol stands in for
// one. A sign is `aria-hidden`: its words are its title or the text beside it. An element is shown, never named.
import { h } from "./util.js";

export const ELEMENTS = ["meadow", "ice", "dust", "void", "lava"];

/** A goal's element as a node (null when the goal has none yet); `dim`: it is not read yet, drawn in the faint ink; `big`: 28 px (else 14). */
export function elem(name, { dim = false, big = false } = {}) {
  return ELEMENTS.includes(name) ? h("span", { class: `ork-elem ${name}${big ? " big" : ""}${dim ? " dim" : ""}`, "aria-hidden": "true" }) : null;
}

/** A sign by its name, 14 px (`big`: 28 px), its words (when it has none beside it) in its title. */
export function sign(name, title = "", { big = false } = {}) {
  return h("span", { class: `ork-sign ${name}${big ? " big" : ""}`, "aria-hidden": "true", title: title || null });
}

// What the host writes where a sign goes (a Today row's mark): the glyph and its sign.
const GLYPHS = { "✓": "check", "✗": "cross", "↻": "work", "☾": "night", "!": "alert", "⚑": "flag", "←": "before", "→": "after" };

/** The sign a glyph of the host stands for (its words in `title`), else the glyph itself as text. */
export function glyph(g, title = "") {
  return GLYPHS[g] ? sign(GLYPHS[g], title) : g;
}

/** The element a new goal of a party will get (spec 50 §2.3, the host's `idea_element.pick`): the one used least among the party's open goals, ties by the order of ELEMENTS. */
export function nextElement(nodes) {
  const used = (nodes || []).filter((n) => n.state !== "done" && n.state !== "dropped").map((n) => n.element);
  return ELEMENTS.reduce((best, e) => (used.filter((u) => u === e).length < used.filter((u) => u === best).length ? e : best), ELEMENTS[0]);
}
