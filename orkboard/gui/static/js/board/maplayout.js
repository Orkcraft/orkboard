// The party's words (docs/specs/39-map.md §3–§4, docs/specs/50-parties-and-goals.md): what a goal's Needs you kind and a task's state say, a task left to do and a
// day in words. The backend writes no words; the faces say them (arena/arenawords.js, goalwords.js).
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** The Needs you kinds on a goal, in words (spec 39 §4.3). */
export const NEEDS_WORDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed", pick: "asks you to pick", pitch: "a pitch judged" };
/** A task's state in words: the preview's task view says it. */
export const TASK_STATE = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", review: "at Review", picking: "asks you to pick", merged: "merged",
  failed: "needs you", held: "held", dropped: "dropped" };

/** A task left to do: not merged, not dropped. */
export const leftToDo = (t) => t.state !== "merged" && t.state !== "dropped";

/** "18 October" from a verdict's time. */
export function flagDate(at) {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`;
}
