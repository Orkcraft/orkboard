// What the one window remembers while it is open (docs/specs/49-one-window.md): which member's work is shown alone, which idea,
// what is hovered, which folds are open. Signals only; nothing is kept past the page (the goal shown is kept by tracks.js `keepGoal`).
import { signal } from "@preact/signals";

export const solo = signal("");            // the member whose work lies across the field alone (§5.3), "" for everyone
export const ideaOn = signal("");          // the idea whose tasks and results are shown alone (§4.2), "" for all
export const ideaHover = signal("");       // the idea hovered in the ideas bar: its tasks light
export const taskHover = signal("");       // "<idea>/<task>" hovered: what waits for it lights (§5.4)
export const ideasOpen = signal(false);    // the ideas bar's list
export const rawOpen = signal(false);      // Planning's New (n) fold
export const doneOpen = signal(false);     // the ideas bar's Done (n) fold
export const narrow = signal(false);       // below 1 024 px (§3)

/** Another goal is shown: what was picked on the last one goes. */
export function clearPicks() {
  solo.value = ""; ideaOn.value = ""; ideaHover.value = ""; taskHover.value = ""; ideasOpen.value = false; rawOpen.value = false; doneOpen.value = false;
}
