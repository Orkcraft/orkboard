// The words the phone's Board, Agents and spec share for spec 35: what a held task waits for (§6, §5), when an idea waits for the limits, and
// the Target's three choices. One place, so the Board's row, the Agents chip and the Stages say it the same way.

export const PRIORITY_WORDS = { high: "High", normal: "Normal", low: "Low" };

export const TARGETS = [
  ["thrift", "Thrift", "lighter models, less reasoning, no proposals at night"],
  ["balance", "Balance", "the usual models and reasoning, two proposals a night"],
  ["quality", "Quality", "heavier models, more reasoning, three proposals a night"],
];
export const targetWord = (id) => (TARGETS.find((t) => t[0] === id) || TARGETS[1])[1];

/** "18:00" from an ISO time (or "" when there is none). */
export function hhmm(iso) {
  const d = new Date(iso);
  return !iso || Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
}

/** A held task's note said in words (spec 35 §11.5): `after 18:00` · `reserve · after 18:00` · `files · <idea>` · `files beside · <idea>`.
 *  `idea`: the title of the idea it waits for, when it is known (`waits_title`). */
export function heldWords(note, idea = "") {
  const n = String(note || "");
  let m = n.match(/^reserve · after (.+)$/);
  if (m) return `keeps your reserve · after ${m[1]}`;
  m = n.match(/^after (.+)$/);
  if (m) return `waits for limits · after ${m[1]}`;
  m = n.match(/^files · (.+)$/);
  if (m) return `waits for ${idea || m[1]} · same files`;
  m = n.match(/^files beside · (.+)$/);
  if (m) return `beside ${idea || m[1]} · same files`;
  return n || "held";
}
