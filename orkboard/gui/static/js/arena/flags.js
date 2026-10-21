// A goal's flag, said once per device (docs/specs/50-parties-and-goals.md §3.8): after a gate's merge that raised flags (`ideas.flags`' `goals` newer than
// this device saw) a line stands over the field until it is closed — *n flags raised · <a>, <b> and k more are in main* —, never over the work and never
// again: the newest `at` seen is kept per project (`localStorage` `orkboard.flags.goals.<project>`), written when the line first stands. A goal's row in
// the Flags fold is lit once. A device with no mark yet (the first start after this part) says nothing of the flags raised before.
import { signal } from "@preact/signals";
import { lookKey } from "../shell/store.js";

export const flagLine = signal(null);          // {n, shorts, party, goals} while the line stands, null when it is closed or there is none
export const litFlags = new Set();             // the goals whose row in Flags (n) is lit once, when it is on screen

const key = () => (lookKey() ? lookKey().replace("orkboard.look.", "orkboard.flags.goals.") : "");
const read = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
const write = (k, v) => { try { localStorage.setItem(k, v); } catch { /* the line is said again next time */ } };

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
  fresh.forEach((f) => litFlags.add(f.slug));
  flagLine.value = { n: goals.length, goals, shorts: [...fresh.map((f) => f.short || f.title), ...(now?.shorts || [])], party: fresh[0].goal };
}

export function closeFlagLine() {
  flagLine.value = null;
}
