// A goal's flag, said once per device (docs/specs/50-parties-and-goals.md §3.8): after a gate's merge that raised flags (`ideas.flags`' `goals` newer than
// this device saw) a line stands over the field until it is closed — *n flags raised · <a>, <b> and k more are in main* —, never over the work and never
// again: the newest `at` seen is kept per project (`localStorage` `orkboard.flags.goals.<project>`), written when the line first stands. A goal's row in
// the Flags fold is lit once. A device with no mark yet (the first start after this part) says nothing of the flags raised before.
// When the line stands, a raise waits (docs/specs/64-flags-raised.md): the new goals' elements travel from the gate to the line (partyline.js `FlagLine`), where the first
// six stay in a row; the box they travel from is the merge's press (gate.js keeps it for 10 s), else the gate's button.
import { batch, signal } from "@preact/signals";
import { lookKey, mapData } from "../shell/store.js";

export const flagLine = signal(null);          // {n, shorts, party, goals, row: [{slug, element}]} while the line stands, null when it is closed or there is none
export const litFlags = new Set();             // the goals whose row in Flags (n) is lit once, when it is on screen
export const raise = signal(null);             // the raise waiting (spec 64 §3): {goals: [{slug, element}], from: the merge's press box | null, at}, one at a time, null with none

export const ROW = 6;                          // the elements a line keeps (and travel)
export const RAISE_KEEP_MS = 6000, MERGE_KEEP_MS = 10000;
let raiseTimer = 0, merged = null;

const key = () => (lookKey() ? lookKey().replace("orkboard.look.", "orkboard.flags.goals.") : "");
const read = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const write = (k, v) => { try { localStorage.setItem(k, v); } catch { /* the line is said again next time */ } };
const box = (r) => ({ left: r.left, top: r.top, width: r.width, height: r.height });

/** The person pressed Merge in the gate's screen: its box is kept for 10 s (the flags it raises come back with the Board). */
export function mergePressed(r) {
  merged = { box: box(r), at: Date.now() };
}
/** The merge was refused: nothing was raised by it. */
export function mergeRefused() {
  merged = null;
}
/** The gate's button, when it is on screen and nothing covers it (the element at its centre is it); else null. Read when the line is drawn, which pushes the field down. */
export function gateButton() {
  const b = document.querySelector(".arena-gate__btn"), r = b?.getBoundingClientRect();
  if (!r || !r.width || !r.height) return null;
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  if (x < 0 || y < 0 || x > innerWidth || y > innerHeight) return null;
  return b.contains(document.elementFromPoint(x, y)) ? box(r) : null;
}

/** The goals just raised wait to travel to the line, from the box of a merge pressed a moment ago (once: the next line does not take it again). Dropped after 6 s. */
function raiseWaits(goals) {
  clearTimeout(raiseTimer);
  const near = merged && Date.now() - merged.at <= MERGE_KEEP_MS ? merged.box : null, mine = { goals, from: near, at: Date.now() };
  merged = null;
  raise.value = mine;
  raiseTimer = setTimeout(() => dropRaise(mine), RAISE_KEEP_MS);
}
/** The raise is played, late or not played: nothing waits. With `mine`, only that raise is dropped. */
export function dropRaise(mine) {
  if (mine && raise.value !== mine) return;
  clearTimeout(raiseTimer);
  raise.value = null;
}

/** The goals of `ideas.flags`, as this device sees them now: starts the line for the ones newer than its mark. */
export function seeFlags(list) {
  const k = key();
  if (!k || !Array.isArray(list)) return;
  const newest = list.reduce((a, f) => (String(f.at) > a ? String(f.at) : a), "");
  const seen = read(k);
  if (seen === null) { write(k, newest || "0"); return; }          // nothing is said of what was raised before this device looked
  const fresh = list.filter((f) => String(f.at) > seen);
  if (!fresh.length) return;
  write(k, newest);
  const now = flagLine.value, goals = [...fresh.map((f) => f.slug), ...(now?.goals || [])];
  const elems = fresh.map((f) => ({ slug: f.slug, element: f.element || mapData.value?.nodes?.find((n) => n.slug === f.slug)?.element || "" }));
  fresh.forEach((f) => litFlags.add(f.slug));
  batch(() => {                                                    // the raise is there in the render that draws the line
    raiseWaits(elems);
    flagLine.value = { n: goals.length, goals, shorts: [...fresh.map((f) => f.short || f.title), ...(now?.shorts || [])], party: fresh[0].goal, row: [...elems, ...(now?.row || [])].slice(0, ROW) };
  });
}

export function closeFlagLine() {
  batch(() => { flagLine.value = null; dropRaise(); });
}
