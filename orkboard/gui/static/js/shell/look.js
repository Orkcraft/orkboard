// The last look (docs/specs/42-coming-back.md §1.3): when the person last pressed, typed or had the page in front of them, kept
// per device and per project as `orkboard.look.<12 characters>` (storage's key is the tabs', js/shell/store.js `lookKey`). A page
// that becomes visible, starts, shows another project or is pressed after a quiet spell, with the last look AWAY_H hours old or
// more, asks `ideas.recap` since it and moves the look to now; a device with no last look writes it and shows nothing. The cards
// to show wait in `cards` (js/board/cards.js draws the first). Everything is read and written in try/catch: the page works without it.
import { signal, effect } from "@preact/signals";
import { command, town } from "../link.js";
import { lookKey, lookTick, logOpened } from "./store.js";

export const AWAY_H = 6;
const WRITE_GAP_MS = 60 * 1000;          // a press moves the look at most once a minute
export const cards = signal([]);         // [{kind: "recap" | "week", data}], the first is shown

const read = (key) => { try { return Number(localStorage.getItem(key)) || 0; } catch { return 0; } };
let lastWrite = 0, checking = false;

/** The last look is now. */
export function touch(now = Date.now()) {
  const key = lookKey();
  if (!key) return;
  try { localStorage.setItem(key, String(now)); } catch { /* the page works without it */ }
  lastWrite = now;
}

/** A card to show: `first` puts it ahead of the one waiting (Last week before the recap). */
export function showCard(card, first = false) {
  cards.value = first ? [card, ...cards.value] : [...cards.value, card];
}

/** The card shown is closed: the next one, if one waits. Closing writes nothing (the last look already moved). */
export function closeCard() {
  cards.value = cards.value.slice(1);
}

// The recap is logged as opened when it is the card shown, not when its answer arrives: it may wait behind Last week's card.
const logged = new WeakSet();
if (typeof window !== "undefined") {
  effect(() => {
    const first = cards.value[0];
    if (first && first.kind === "recap" && !logged.has(first)) { logged.add(first); queueMicrotask(() => logOpened("recap", `${first.data.hours}h`)); }
  });
}

// -- Last week (spec 42 §7.3): the first look of a new ISO week shows last week's card; `orkboard.week.<12 characters>` holds the last week shown --------
const weekKey = () => lookKey().replace("orkboard.look.", "orkboard.week.");
/** The ISO week (`2026-W42`) of a date. */
export function isoWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const year = d.getUTCFullYear();
  return `${year}-W${String(Math.ceil(((d - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7)).padStart(2, "0")}`;
}
const lastWeekId = () => isoWeek(new Date(Date.now() - 7 * 86400000));
let weekBusy = false;

/** On the first look of a new week the card of last week comes first (a device with no key writes it and shows nothing). */
export async function weekCheck() {
  const key = weekKey();
  if (!key || weekBusy || !town.value || (typeof document !== "undefined" && document.visibilityState === "hidden")) return;
  const last = lastWeekId();
  let kept = null;
  try { kept = localStorage.getItem(key); } catch { return; }
  const write = (week) => { try { localStorage.setItem(key, week); } catch { /* the page works without it */ } };
  if (kept === last) return;
  if (kept === null) { write(last); return; }
  weekBusy = true;
  try {
    const got = await command("ideas.week", {}).catch(() => null);
    if (!got || got.error || key !== weekKey()) return;
    write(got.week);                                  // the week `ideas.week` answered, not this device's idea of last week
    if (!got.empty && got.week !== kept) {
      showCard({ kind: "week", data: got }, true);
      logOpened("week", got.week);
    }
  } finally { weekBusy = false; }
}

/** The Map's *Last week* link: the card at any time. */
export async function showWeek() {
  const got = await command("ideas.week", {}).catch(() => null);
  if (!got || got.error) return;
  cards.value = [{ kind: "week", data: got }, ...cards.value.filter((c) => c.kind !== "week")];
  logOpened("week", got.week, "map");
}

/** The Board's page is in front of the person: when the last look is old, ask what happened since; else keep the look fresh. */
export async function away() {
  weekCheck();
  const key = lookKey();
  if (!key || checking || !town.value || (typeof document !== "undefined" && document.visibilityState === "hidden")) return;
  const last = read(key), now = Date.now();
  if (!last) { touch(now); return; }
  if (now - last < AWAY_H * 3600 * 1000) { if (now - lastWrite >= WRITE_GAP_MS) touch(now); return; }
  checking = true;
  try {
    const got = await command("ideas.recap", { since: last }).catch(() => null);
    if (!got || got.error || key !== lookKey()) return;
    touch(Date.now());
    if (got.merged && !got.empty) {
      showCard({ kind: "recap", data: got });
    }
  } finally { checking = false; }
}

if (typeof window !== "undefined") {
  effect(() => { lookTick.value; cards.value = []; queueMicrotask(away); });         // another project is shown, or the page starts
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "hidden") touch(); else away(); });
  window.addEventListener("pagehide", () => touch());
  for (const type of ["pointerdown", "keydown"]) window.addEventListener(type, () => away(), true);
}
