// What the one window remembers while it is open (docs/specs/49-one-window.md, docs/specs/50-parties-and-goals.md): which member's work is
// shown alone, which goals of the party are picked (the filter) or peeked, what is hovered, which folds are open and which stack is spread.
// Signals only; nothing is kept past the page (the party shown is kept by tracks.js `keepGoal`, the flag line's watermark by flags.js).
import { signal } from "@preact/signals";

export const solo = signal("");            // the member whose work lies across the field alone (spec 49 §5.3), "" for everyone
export const picks = signal({});           // party slug → the goals picked into the filter (spec 50 §3.5), kept per party for the session
export const peek = signal("");            // the goal under the pointer in the goals list: the board shows only its cards while it is there
export const taskHover = signal("");       // "<goal>/<task>" hovered or focused: what it waits for and what waits for it light and are drawn (§3.4)
export const taskHoverBy = signal("");     // "pointer" or "focus": who hovered it (the arrows are drawn for a fine pointer, and for the keyboard's focus always)
export const rawOpen = signal(false);      // the goals list's New (n) fold
export const flagsOpen = signal(false);    // its Flags (n) fold
export const flagsAll = signal(false);     // ... listed in full (All n), not the newest ten
export const spread = signal(null);        // the stack spread over the field: {goal, member, row, keys, from} (§3.6), null with none
export const narrow = signal(false);       // below 1 024 px (spec 49 §3)

/** The goals of a party the board shows: the one peeked, else the ones picked; [] shows all (§3.5). */
export const shownGoals = (party) => (peek.value ? [peek.value] : picks.value[party] || []);
/** A press on a goal's row: picked, or taken out when it was. */
export function togglePick(party, goal) {
  const now = picks.value[party] || [];
  picks.value = { ...picks.value, [party]: now.includes(goal) ? now.filter((x) => x !== goal) : [...now, goal] };
}
export function clearPicks(party) {
  if (party === undefined) { picks.value = {}; } else if ((picks.value[party] || []).length) { picks.value = { ...picks.value, [party]: [] }; }
  peek.value = "";
}

/** Another party is shown: what was hovered, spread or opened on the last one goes (the picks stay with their party). */
export function leaveParty() {
  solo.value = ""; peek.value = ""; taskHover.value = ""; spread.value = null; rawOpen.value = false; flagsOpen.value = false; flagsAll.value = false;
}
