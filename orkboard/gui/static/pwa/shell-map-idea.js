// What the goal's window keeps of an idea on the Map (docs/specs/48-map-ideas.md, spec 49 §10): the three stages and their words, the
// words of a task and of a member's state, and the stage an idea is in. The idea's card, its lanes and its stacks went with the Map: the
// goal's window (shell-arena.js) draws the party's columns instead, and the stops along the bottom (shell-stops.js) hold what waits for the person.
export const STAGES = [["planning", "Planning"], ["implementation", "Implementation"], ["checking", "Checking"]];
export const STAGE_WORDS = Object.fromEntries(STAGES);
export const NEEDS = { asks: "asks you", plan: "plan ready", todo: "a to-do waits", failed: "failed", proposal: "proposed", pick: "asks you to pick" };
export const TASK_WORDS = { waiting: "waiting", ready: "queued", running: "working", testing: "testing", picking: "asks you to pick", review: "in Review", failed: "needs you", held: "held" };
const MEMBER_WORDS = { work: "at work", next: "next", tonight: "tonight", free: "free" };

/** The stage an idea is in: the host's, else made from its tasks (an older host). */
export const stageOf = (n) => n.stage || (n.state === "done" ? "done" : (n.tasks || []).length && n.state === "working" ? "implementation" : "planning");

/** A member's state in words: *at work*, *next*, *tonight*, *free*, or the Needs you words (`why`); its sign (↻, the clock) is drawn beside them. */
export const memberWords = (state, why) => (state === "needs" ? NEEDS[why] || "needs you" : MEMBER_WORDS[state] || "free");
