// A goal by stage (docs/specs/48-map-ideas.md): the words a member's state and a goal's price say. Pure functions over `ideas.map`; the backend writes no words.
import { NEEDS_WORDS } from "./maplayout.js";

/** A member's state in words (spec 48 §3.2): *at work*, *next*, *tonight*, *free*, or the Needs you words. */
export function memberWords(m) {
  if (m.state === "needs") return NEEDS_WORDS[m.why] || "needs you";
  return { work: "at work", next: "next", tonight: "tonight", free: "free" }[m.state] || "";
}

/** *plan ≈$1–2*. */
export const planWords = (e) => (e ? `plan ≈$${Math.round(e.usd_low * 100) / 100}–${Math.round(e.usd_high * 100) / 100}` : "");

/** *≈$0.84 so far*, "" when unpriced. */
export const soFarWords = (usd) => (usd == null ? "" : `≈$${usd < 10 ? usd.toFixed(2) : Math.round(usd)} so far`);

/** *today 2 merged · ≈$1.15*. */
export const todayWords = (t) => (t ? `today ${t.merged} merged · ≈$${t.usd.toFixed(2)}` : "");
