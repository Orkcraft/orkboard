// The project's level in words (docs/specs/70-orkmaster-and-the-project.md, decisions §85): pure functions over `ideas.map` (its parties, their goals, `project`: the Orkmaster and the deal) and `ideas.party_for`.
// No signal and no template here; project.js, projectdeal.js and projectparty.js draw what these say. The words are the glossary's (realm/lexicon.py `orkmaster`, `project_level`): a goal is a deck only in the code.
import { atWork, planningOf } from "./arenawords.js";
import { flagWords, workLine } from "./goalwords.js";
import { pitchWords } from "./pitchwords.js";

export const THE_PROJECT = "The project";
export const PARTIES_WORDS = "The parties, their goals";

/** The groups of a column, in order. */
export const GROUPS = [["planning", "Planning"], ["work", "At work"], ["waits", "Waits for main"]];

const doneOf = (n) => n.state === "done" || n.stage === "done";

/** A party's goals as the column groups them: Planning (a goal not read, or waiting on its plan), At work, Waits for main (done, no flag yet) and Flags (done and flagged, the newest first), each
 *  `[{n, words}]`: the goal and its state in the words a goal row of the party says. Ideation's pitches (spec 65): the ones to judge and being judged are Planning, a sent one At work (its goal went on);
 *  a passed one is not shown. */
export function decksOf(g, nodes) {
  const lead = g.leader?.name || "Taskmaster", out = { planning: [], work: [], waits: [], flags: [] };
  if (g.ideation) {
    for (const n of nodes) {
      const st = n.pitch?.state || n.state, deck = { n, words: pitchWords(n) };
      if (st === "sent") out.work.push(deck);
      else if (st !== "passed") out.planning.push(deck);
    }
    return out;
  }
  const plan = planningOf(g, nodes, lead), rows = new Map([...plan.rows, ...plan.raw].map((r) => [r.slug, r.words]));
  for (const n of nodes) {
    if (doneOf(n)) (n.flag ? out.flags : out.waits).push({ n, words: n.flag ? flagWords(n.flag) : "in dev · waits for main" });
    else if (atWork(n)) out.work.push({ n, words: workLine(n) });
    else out.planning.push({ n, words: rows.get(n.slug) || n.state });
  }
  out.flags.sort((a, b) => String(b.n.flag.at).localeCompare(String(a.n.flag.at)));
  return out;
}

/** How many decks a column holds. */
export const deckCount = (d) => d.planning.length + d.work.length + d.waits.length + d.flags.length;

/** *Nothing in <party> yet*. */
export const emptyWords = (name) => `Nothing in ${name} yet`;

/** The links the routes draw between the decks (spec 70 §2.3): [{key: "<from>><to>", from, to}], a goal's pitch to it and it to the release it went into, only between decks in different columns.
 *  `nodes`: every goal of the map. A pitch's own `goal_state` says the same from its side (the goal it became, the release that went into). */
export function linksOf(nodes) {
  const party = new Map(nodes.map((n) => [n.slug, n.goal])), seen = new Set(), out = [];
  const add = (from, to) => {
    const key = `${from}>${to}`;
    if (!party.has(from) || !party.has(to) || party.get(from) === party.get(to) || seen.has(key)) return;
    seen.add(key);
    out.push({ key, from, to });
  };
  for (const n of nodes) {
    for (const s of n.route || []) {
      if (s.step === "pitch") add(s.goal, n.slug);
      else if (s.step === "release") add(n.slug, s.goal);
    }
    const gs = n.goal_state;
    if (gs?.goal) {
      add(n.slug, gs.goal);
      if (gs.release?.goal) add(gs.goal, gs.release.goal);
    }
  }
  return out;
}

/** The goal types a New goal on the project's level offers (spec 70 §4.1): the union of the parties' own, a type once, with no one missing (the Orkmaster says who is, once a party is picked). */
export function typesOf(goals) {
  const seen = new Set(), out = [];
  for (const g of goals) {
    for (const t of g.types || []) if (!seen.has(t.id)) { seen.add(t.id); out.push({ ...t, missing: [] }); }
  }
  return out;
}

/** What a deal card says of its why: *3 flags wait and no party releases them*, *No party judges small ideas yet*, *You have one* (muted). "" for none. */
export function whyWords(entry) {
  if (!entry) return "";
  if (entry.why === "flags_wait") return entry.n === 1 ? "1 flag waits and no party releases it" : `${entry.n} flags wait and no party releases them`;
  if (entry.why === "no_pitches") return "No party judges small ideas yet";
  if (entry.why === "have") return "You have one";
  return "";
}

/** A preset's entry in the deal, or null (an older host has no deal). */
export const dealEntry = (deal, id) => (deal || []).find((d) => d.id === id) || null;

/** The presets in the deal's order (a preset the deal does not name keeps its place after the others); `deal` empty: as they are. */
export function inDealOrder(presets, deal) {
  if (!deal?.length) return presets;
  const rank = (p) => { const i = deal.findIndex((d) => d.id === p.id); return i < 0 ? deal.length : i; };
  return presets.map((p, i) => [p, i]).sort(([a, i], [b, j]) => rank(a) - rank(b) || i - j).map(([p]) => p);
}

/** *Orkmaster suggests Passkey*. */
export const suggestsWords = (name) => `Orkmaster suggests ${name}`;

/** A party's fit for a goal type, in words: *takes it whole*, *needs Artist*, *no one there does it*; Ideation with no type: *a pitch*; "" otherwise. */
export function fitWords(p) {
  if (p.fits === "whole") return "takes it whole";
  if (p.fits === "missing") return `needs ${(p.missing || []).map((m) => m.name).join(", ")}`;
  if (p.fits === "none") return "no one there does it";
  if (p.fits === "pitch") return "a pitch";
  return "";
}
