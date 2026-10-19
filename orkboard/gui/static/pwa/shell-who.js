// Who does a task, on the phone (decisions §53; the desktop's js/orkui.js): the head of the agent's craft's race in orkUI
// (an ork engineers, an elf designs, a goblin minds the data, a gnome markets), the gear on its head its tier (a novice bare,
// a seasoned in iron, a veteran hooded). A head never stands alone: its words are beside it or in its title.
import { h, head as raceHead } from "./util.js";

// The words of a head, as realm/lexicon.py says them (tier.*, race.*, craft.*; tests/test_design_system.py keeps them so).
export const TIER_WORDS = { elder: "Veteran", warrior: "Seasoned", laborer: "Novice" };
export const RACE_WORDS = { peon: "ork", elf: "elf", goblin: "goblin", gnome: "gnome" };
export const CRAFT_WORDS = { engineering: "Engineering", design: "Design", data: "Data", marketing: "Marketing" };

/** "Seasoned elf · Design": what a head says, in words. */
export const headWords = (head) => (head ? `${TIER_WORDS[head.tier] || ""} ${RACE_WORDS[head.race] || ""} · ${CRAFT_WORDS[head.craft] || ""}` : "");

/** The head alone (`head`: {craft, race, tier} as the host sends it), its words in its title; `small` in a line of text. */
export function whoHead(head, small = false) {
  return head ? raceHead(head.race, head.tier, { small, title: headWords(head) }) : null;
}

/** A goal's mark: the head of its craft's race, bare (a goal has no tier), its craft in words in its title. */
export const goalHead = (g, small = false) => raceHead(g?.race || "peon", "laborer", { small, title: CRAFT_WORDS[g?.craft] || CRAFT_WORDS.engineering });

/** A goal's mark: the heads of its team (at most three, its agents' as Agents draws them), else its craft's head. */
export function goalMark(g, roleList = [], small = false) {
  const heads = (g?.team || []).map((s) => roleList.find((r) => r.slug === s)?.head).filter(Boolean).slice(0, 3);
  if (!heads.length) return goalHead(g, small);
  return h("span", { class: "team-mark-heads" }, ...heads.map((hd) => whoHead(hd, small)));
}

/** A head beside its words: the tier, then the race and the craft, muted (orkUI's .ork-race). */
export function who(head, small = false) {
  if (!head) return null;
  return h("span", { class: `ork-race${small ? " small" : ""}`, "data-race": head.race, "data-tier": head.tier }, raceHead(head.race, head.tier, { small }),
    h("span", { class: "ork-race__word" }, `${TIER_WORDS[head.tier]} `, h("span", { class: "ork-race__tier" }, `${RACE_WORDS[head.race]} · ${CRAFT_WORDS[head.craft]}`)));
}
