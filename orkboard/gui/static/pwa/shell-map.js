// What the goal's window keeps of the Map (docs/specs/39-map.md, spec 42 §2, spec 49 §10, spec 50): why a node does not move in words (the Map's own words: §4.3's, as the Agents' chips) and a party's
// old flag in words (a verdict met, kept as history: *Before: met, says Product manager · 18 October* in About this party). The goals' flags are shell-goals.js's and shell-party.js's.
import { hhmm } from "./shell-words.js";
import { NEEDS } from "./shell-map-idea.js";

/** "18:00" from a bare "HH:MM" or an ISO time. */
const until = (u) => (/^\d{1,2}:\d{2}$/.test(String(u || "")) ? u : hhmm(u));

/** Why a node that is not done does not move, in words (the Map's own words: §4.3's, as the Agents' chips). "" when it moves. */
export function waitsWords(node) {
  const w = node.waits;
  if (!w || node.state === "done") return "";
  const at = until(w.until);
  if (w.kind === "you") return NEEDS[node.needs_you] || "needs you";
  if (w.kind === "idea") return `waits for ${w.title || w.ref}`;
  if (w.kind === "files") return `same files as ${w.title || w.ref}`;
  if (w.kind === "limits") return at ? `waits for limits · after ${at}` : "waits for limits";
  if (w.kind === "reserve") return at ? `keeps your reserve · after ${at}` : "keeps your reserve";
  if (w.kind === "night") return "tonight";
  if (w.kind === "stopped") return "stopped";
  if (w.kind === "week") return `waits: the week is behind${w.until ? ` · until ${dayAt(w.until)}` : ""}`;
  return "";
}

/** "Mon 09:00" from a local `YYYY-MM-DDTHH:MM`; "" when it does not read. */
const dayAt = (iso) => {
  const d = new Date(iso);
  return !iso || Number.isNaN(d.getTime()) ? "" : `${d.toLocaleDateString("en-US", { weekday: "short" })} ${hhmm(iso)}`;
};

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
/** *met, says Product manager · 18 October* (spec 42 §2.4). */
export function flagWords(f) {
  const d = new Date(f.at);
  return [`met, says ${f.by}`, Number.isNaN(d.getTime()) ? "" : `${d.getDate()} ${MONTHS[d.getMonth()]}`].filter(Boolean).join(" · ");
}
