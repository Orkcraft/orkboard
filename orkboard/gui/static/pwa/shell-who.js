// Who does a task, on the phone (decisions §53; the desktop's js/orkui.js): the head of the agent's craft's race in orkUI
// (an ork engineers, an elf designs, a goblin minds the data, a gnome markets), the gear on its head its tier (a novice bare,
// a seasoned in iron, a veteran hooded). A head never stands alone: its words are beside it or in its title.
import { h, head as raceHead } from "./util.js";

// The words of a head, as realm/lexicon.py says them (tier.*, race.*, craft.*; tests/test_design_system.py keeps them so).
export const TIER_WORDS = { elder: "Veteran", warrior: "Seasoned", laborer: "Novice" };
export const RACE_WORDS = { peon: "ork", elf: "elf", goblin: "goblin", gnome: "gnome", lich: "lich" };
export const CRAFT_WORDS = { engineering: "Engineering", design: "Design", data: "Data", marketing: "Marketing", product: "Product" };

/** "Seasoned elf · Design": what a head says, in words. */
export const headWords = (head) => (head ? `${TIER_WORDS[head.tier] || ""} ${RACE_WORDS[head.race] || ""} · ${CRAFT_WORDS[head.craft] || ""}` : "");

/** The head alone (`head`: {craft, race, tier} as the host sends it), its words in its title; `small` in a line of text. */
export function whoHead(head, small = false) {
  return head ? raceHead(head.race, head.tier, { small, title: headWords(head) }) : null;
}

/** A goal's mark: the head of its craft's race, bare (a goal has no tier), its craft in words in its title. */
/** A goal's head: its leader's (decisions §53), else its craft's. */
export const goalHead = (g, small = false) => (g?.leader?.head ? raceHead(g.leader.head.race, g.leader.head.tier, { small, title: `Led by ${g.leader.name}` })
  : raceHead(g?.race || "peon", "laborer", { small, title: CRAFT_WORDS[g?.craft] || CRAFT_WORDS.engineering }));

/** A goal's mark: its leader's head, then its party's (at most four, as Agents draws them), else its craft's head. */
export function goalMark(g, roleList = [], small = false) {
  const party = (g?.team || []).map((s) => roleList.find((r) => r.slug === s)?.head).filter(Boolean);
  const heads = [...(g?.leader?.head ? [g.leader.head] : []), ...party].slice(0, 4);
  if (!party.length) return goalHead(g, small);
  return h("span", { class: "team-mark-heads" }, ...heads.map((hd) => whoHead(hd, small)));
}

/** A head at 36 × 33 from its @2x image (orkUI's `.ork-race__head.mid`): a member's, and a stop's in its middle. */
export const midHead = (head) => (head ? h("img", { class: "ork-race__head mid", src: `races/${head.race}-${head.tier}@2x.png`, width: 36, height: 33, alt: "", title: headWords(head), draggable: "false" }) : null);

/** One of orkUI's marks (an AI tool's `harness-<id>`, a level's `rank-<n>`) at 16 × 16 from its @2x image, beside a name. */
export const mark = (name, tip = "", extra = "") => h("img", { class: `ork-mark${extra ? ` ${extra}` : ""}`, src: `marks/${name}.png`, srcset: `marks/${name}@2x.png 2x`, width: 16, height: 16, alt: "", title: tip || null, draggable: "false" });

/** A head beside its words: the tier, then the race and the craft, muted (orkUI's .ork-race). */
export function who(head, small = false) {
  if (!head) return null;
  return h("span", { class: `ork-race${small ? " small" : ""}`, "data-race": head.race, "data-tier": head.tier }, raceHead(head.race, head.tier, { small }),
    h("span", { class: "ork-race__word" }, `${TIER_WORDS[head.tier]} `, h("span", { class: "ork-race__tier" }, `${RACE_WORDS[head.race]} · ${CRAFT_WORDS[head.craft]}`)));
}
