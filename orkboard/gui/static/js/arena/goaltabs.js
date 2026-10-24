// The parties' data and the gather (docs/specs/69-parties-in-the-column.md, decisions §84; it was the party's deck, spec 52 §3, decisions §65.3, and before that the top
// bar's party switch, spec 50 §3.1): which party the board shows (`shownOf`: the picked one, else the one kept for this device and project, else the first), what the
// project's parties are with their stops (`partiesOf`; a stop is counted only where it cannot be seen, §65.2: `othersStops`) and the new party's heads gathering onto
// its heading's head (`gatherInto`, spec 63 §3). The list that draws them is partylist.js; the deck and the parties' spread are gone from the desktop (the phone keeps its own).
import { ORKUI } from "../orkui.js";
import { town } from "../link.js";
import { board, OPS, goalList } from "../board/store.js";
import { keptGoal } from "../board/tracks.js";
import { mapData } from "../shell/store.js";
import { APART_MS, LIT_MS } from "./motion.js";
import { goalsOf, nodesOf, opStopsOf, stopsOf } from "./arenawords.js";

/** The party shown: the picked one if the Map has it (or Operations, or the Board has it and the Map comes a moment later: a party just saved), else the
 *  one kept for this project, else the first. */
export function shownOf(goals, picked) {
  if (picked === OPS || goals.some((g) => g.slug === picked) || goalList().some((g) => g.slug === picked)) return picked;
  return (goals.find((g) => g.slug === keptGoal()) || goals[0])?.slug || "";
}

const opsOn = () => town.value?.ops_rev !== undefined;
const opStops = (needs) => opStopsOf(needs).length;
const hurt = (stops) => stops.some((s) => s.tone === "danger");               // one of them failed: the dot is the danger colour
export const atWork = (g) => (g.party || []).some((x) => x.state === "work") || g.state === "reading";

/** The project's parties as the list holds them: [{g, nodes, stops, failed, working}], and whether Operations is one more. */
export function partiesOf() {
  const m = mapData.value, needs = board.value?.needs_you || [];
  const goals = goalsOf(m, goalList().map((g) => g.slug));
  return { goals: goals.map((g) => { const nodes = nodesOf(m, g.slug); const mine = stopsOf(needs, g, nodes); return { g, nodes, stops: mine.length, failed: hurt(mine), working: atWork(g) }; }),
    ops: opsOn(), opStops: opStops(needs), opFailed: hurt(opStopsOf(needs)) };
}

/** The stops that wait in the project's other parties and in Operations: those of every party but the one shown. */
export function othersStops(shown) {
  const { goals, ops, opStops: o } = partiesOf();
  return goals.filter((x) => x.g.slug !== shown).reduce((k, x) => k + x.stops, 0) + (ops && shown !== OPS ? o : 0);
}

const GATHER_MS = 300, GATHER_SCALE = 0.4;     // a gathered head's travel (the deal's steps, arena.css `arena-gather`), and how large it is when it lands

/** A new party's heads gather onto its heading's head (spec 63 §3.2, docs/specs/69-parties-in-the-column.md §4): a copy of each head (`from`: [{race, tier, box}], the leader's first) travels over the page from its seat's box to the head's centre at 0.4 of its
 *  size, 35 ms after the one before, and is gone on landing; when the last has landed the head is lit once, as the quiet reward. The copies take no press and remove themselves. */
export function gatherInto(deck, from) {
  const d = deck.getBoundingClientRect(), cx = d.left + d.width / 2, cy = d.top + d.height / 2;
  if (!from.length || !d.width || typeof deck.animate !== "function") return;
  let left = from.length, lit = false;
  const light = () => {
    if (lit) return;
    lit = true;
    copies.forEach((c) => c.remove());
    if (deck.isConnected) deck.animate([{ background: "var(--ork-ink)", color: "var(--ork-on-ink)" }, { background: "transparent" }], { duration: LIT_MS, easing: "steps(4, end)" });
  };
  const copies = from.map(({ race, tier, box }, i) => {
    const img = document.createElement("img");
    img.className = "ork-race__head arena-gather";
    img.src = `${ORKUI}/races/${race}-${tier}@2x.png`;
    img.alt = "";
    Object.assign(img.style, { left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px`, height: `${box.height}px` });
    img.style.setProperty("--dx", `${cx - (box.left + box.width / 2)}px`);
    img.style.setProperty("--dy", `${cy - (box.top + box.height / 2)}px`);
    img.style.setProperty("--s", String(GATHER_SCALE));
    img.style.setProperty("--delay", `${i * APART_MS}ms`);
    img.addEventListener("animationend", () => { img.remove(); if (--left === 0) light(); }, { once: true });
    document.body.append(img);
    return img;
  });
  setTimeout(light, GATHER_MS + APART_MS * from.length + 500);        // a page that never played them (a tab sent away) leaves nothing behind
}
