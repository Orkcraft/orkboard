// A goal's route and its release in words (docs/specs/68-release-and-route.md §0, §7): pure functions over the host's `route` steps (`ideas.page`, `ideas.map` nodes), a pitch's `goal_state`, a flag's `release`
// and a release goal's own `release`. The desktop says what the phone says (pwa/shell-goals-words.js): a step is *At work in <party> · k of n* only while its goal is `working`, else *In <party>*.
import { mapData } from "../shell/store.js";
import { flagDay } from "./goalwords.js";

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;
const join = (...parts) => parts.filter(Boolean).join(" ");
const kOfN = (done, total) => (total ? ` · ${done || 0} of ${total}` : "");

/** A party's short name by its slug, from the Map (the slug itself when the Map does not have it). */
export function partyName(slug) {
  const g = (mapData.value?.goals || []).find((x) => x.slug === slug);
  return g ? g.short || g.title || slug : slug || "";
}

/** The party the Map has by its slug, or null. */
export const partyOf = (slug) => (mapData.value?.goals || []).find((x) => x.slug === slug) || null;

/** Whether the project has a Release party (its leader is the Release manager): a flag then waits for a release or is in one. */
export const hasReleaseParty = () => (mapData.value?.goals || []).some((g) => g.leader?.slug === "release-manager");

/** Where a goal is in its party: *At work in Mobile app · 3 of 7* while it works, else *In Mobile app* (its work not started, or done and not in main yet). */
const inParty = (g, name) => (g.state === "working" ? `At work in ${name(g.party)}${kOfN(g.done, g.total)}` : `In ${name(g.party)}`);

/** What a pitch's goal is now as the pitch says it (`goal_state`): *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* · *Out in 1.4* · *Dropped*. */
export function goalStateWords(gs, name = partyName) {
  if (!gs) return "";
  if (gs.state === "dropped") return "Dropped";
  const r = gs.release;
  if (r) return r.out ? join("Out in", r.version) : join("In", name(r.party), r.version);
  if (gs.flag) return "In main";
  return inParty(gs, name);
}

/** What a step of a goal's route says: *From Ideation: Invest, 22 Oct* · *Moved from Mobile app* · *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* · *Out in 1.4*. */
export function routeWords(step, name = partyName) {
  switch (step.step) {
    case "pitch": return `From ${name(step.party)}: ${[step.word || step.answer, flagDay(step.at)].filter(Boolean).join(", ")}`;
    case "moved": return `Moved from ${name(step.from || step.party)}`;
    case "party": return inParty(step, name);
    case "main": return "In main";
    case "release": return step.out ? join("Out in", step.version) : join("In", name(step.party), step.version);
    default: return "";
  }
}

/** A flag's release in a party's Flags: *In Release 1.4* · *Out in 1.4* · *Waits for a release* (only in a project with a Release party); "" otherwise. A release's own row says its version and goals (`releaseLine`). */
export function flagRelease(n, name = partyName) {
  if (n.release) return "";
  const r = n.flag?.release;
  if (r) return r.out ? join("Out in", r.version) : join("In", name(r.party), r.version);
  return hasReleaseParty() ? "Waits for a release" : "";
}

/** *1.4 · 3 goals* (a release's row in the Release party's Flags), *Out in 1.4* once it is out. */
export const releaseLine = (own) => (own.out ? join("Out in", own.version) : [own.version, plural((own.goals || []).length, "goal")].filter(Boolean).join(" · "));

/** *3 flags wait for a release* (*1 flag waits for a release*). */
export const waitWords = (n) => `${plural(n, "flag")} ${n === 1 ? "waits" : "wait"} for a release`;

/** The question before a release is marked out. */
export const outAsk = (version) => `Is ${version || "it"} out in the stores? Orkboard submits nothing: say so once you have.`;
