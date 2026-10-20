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

/** `Mon 09:00` from a local ISO time (the week's reset); a bare `09:00` stays as it is. */
export function dayAt(iso) {
  const d = new Date(iso);
  if (!/^\d{4}-/.test(String(iso || "")) || Number.isNaN(d.getTime())) return hhmm(iso);
  return `${d.toLocaleDateString([], { weekday: "short" })} ${hhmm(iso)}`;
}

/** What the week's pace means for Low work, in words (spec 44 §5). */
const PACE_WORDS = { ahead: "Low work starts by day", even: "Low work waits for the night", behind: "Low work waits until the week comes back" };

/** *The week: 55 % left with 2 days to go: Low work starts by day*; "" without a week. */
export function weekPaceWords(w) {
  const k = w && w.week;
  if (!k || !PACE_WORDS[k.pace]) return "";
  const days = Math.max(0, Math.round(k.rest * 7));
  return `The week: ${Math.round(k.left * 100)} % left with ${days} ${days === 1 ? "day" : "days"} to go: ${PACE_WORDS[k.pace]}`;
}
export const lastUnusedWords = (w) => (!w || w.last_unused == null ? "" : `Last week ended with ${Math.round(w.last_unused * 100)} % unused`);

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
