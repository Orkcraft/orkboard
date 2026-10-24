// Ideation's pitches in words (docs/specs/65-ideation.md §2, §8): pure functions over `ideas.map`'s nodes of a party the Investor leads (a node's
// `pitch`, realm/pitches.py `face`) and `ideas.page`'s `pitch`. A pitch is a goal of Ideation: judged by four views, the Skeptic's case against and
// the Investor's decision, never built. No signal and no template here; pitches.js (the line on the field, the left column) and shell/pitchview.js
// (a pitch's screen) draw what these say.
import { board, goalList } from "../board/store.js";
import { plural, waitsWords } from "./arenawords.js";
import { goalStateWords } from "./releasewords.js";

export const INVESTOR = "investor";                       // realm/library.py INVESTOR: the leader whose party is Ideation
export const VIEWS = 4;                                    // the views every pitch is read by (realm/library.py VIEWS)

/** Whether a party is Ideation: the Map says it (`ideation`), else its leader is the Investor (a party the Map has not read yet). `map`: `ideas.map`. */
export function isIdeation(map, slug) {
  const g = (map?.goals || []).find((x) => x.slug === slug);
  if (g) return !!g.ideation || g.leader?.slug === INVESTOR;
  return goalList().find((x) => x.slug === slug)?.leader?.slug === INVESTOR;
}

/** What a pitch's state means, under its title on its screen. */
export const PITCH_STATE = { raw: "Waits to be judged: now, tonight or when you say", judging: "The four views read it, each alone; then the Skeptic and the Investor",
  judged: "Judged: it waits for you", sent: "Sent: its goal is in its party now", passed: "Passed: kept with its why", failed: "A call failed: try again" };

/** How many of a pitch's views have answered. */
export const answered = (p) => (p?.views || []).filter((v) => v.answered).length;

/** Where a judging pitch is: *k of 4 views*, then *the case against*, then *the Investor decides*. */
export function judgingWords(p) {
  const k = answered(p);
  if (k < VIEWS) return `judging · ${k} of ${VIEWS} views`;
  return p?.case ? `${p?.investor?.name || "the Investor"} decides` : "the case against";
}

/** *the Ship party, as Fix a bug*: where a decision would take the pitch, "" when it names no party. A preset the project lacks says so. */
export function whereWords(d) {
  const w = d?.where;
  if (!w?.party) return "";
  return `the ${w.name || w.party} party${w.type_name ? `, as ${w.type_name}` : ""}${w.preset ? " (not in this project yet)" : ""}`;
}

/** A decision in a few words: *Invest · the Ship party, as Fix a bug*, *Reshape*, *Pass*. */
export const decisionWords = (d) => (d ? [d.word, d.answer === "invest" ? whereWords(d) : ""].filter(Boolean).join(" · ") : "");

/** *sent to Ship · Offline mode*: a pitch sent, naming its party and the goal it became. */
export const sentWords = (s) => (s ? `sent to ${s.name || s.party}${s.title ? ` · ${s.title}` : ""}` : "sent");

/** A pitch's line in words, by its state (the left column, the field and the drawer's bar): *on hold*, *tonight*, *judging · 2 of 4 views*,
 *  *judged: Invest*, *sent to Ship · …*, *passed*, *failed · stopped*. `n`: a node of the Map (or a page) with its `pitch`. */
export function pitchWords(n) {
  const p = n?.pitch, st = p?.state || n?.state;
  if (st === "judging") return judgingWords(p);
  if (st === "judged") return `judged: ${p?.decision?.word || "—"}`;
  if (st === "sent") return goalStateWords(n?.goal_state || p?.goal_state) || sentWords(p?.sent);       // the sent goal's state as spec 68 §2.4 has it (an older host sends none: where it went)
  if (st === "passed") return "passed";
  if (st === "failed") {                                   // its error: the page's, else the Board's (a Map node carries none)
    const why = n?.state_error || (board.value?.ideas || []).find((i) => i.slug === n?.slug)?.state_error || "";
    return `failed${why ? ` · ${why}` : ""}`;
  }
  if (n?.waits?.kind === "limits" || n?.waits?.kind === "reserve" || n?.waits?.kind === "week") return waitsWords(n.waits);
  if (n?.queue === "hold") return "on hold · judged when you say";
  if (n?.queue === "night") return "tonight";
  return "next · judged in a moment";
}

/** The sign at a pitch's row: work while it is judged, alert when its decision waits for you, cross when it failed, night tonight. */
export function pitchMark(n) {
  const st = n?.pitch?.state || n?.state;
  if (st === "judging") return { sign: "work", tone: "", label: "being judged" };
  if (st === "judged") return { sign: "alert", tone: "alert", label: "its decision waits for you" };
  if (st === "failed") return { sign: "cross", tone: "danger", label: "it failed" };
  if (st === "raw" && n?.queue === "night") return { sign: "night", tone: "", label: "tonight" };
  return { sign: "", tone: "", label: "" };
}

/** Ideation's pitches by where they lie (§8): judging (with the ones that failed), judged, new (raw: Now, Tonight, Hold), sent, passed (folded). */
export function pitchLists(nodes) {
  const of = (...states) => nodes.filter((n) => states.includes(n.pitch?.state || n.state));
  return { judging: of("judging", "failed"), judged: of("judged"), raw: of("raw"), sent: of("sent"), passed: of("passed") };
}

/** Ideation's leader's work as `planningOf` says a party's (arenawords.js): the pitches being judged (`busy`, *judging*) and the judged ones (its stops) as rows,
 *  the new ones apart (*next: judges “…”*), so that the leader's peek and the party line say the Investor's work. */
export function pitchPlanning(nodes) {
  const row = (n, stop, busy) => ({ slug: n.slug, title: n.short || n.title, full: n.title, stop, busy, mark: stop ? "alert" : busy ? "work" : "", words: pitchWords(n),
    cost: "", kind: "idea", node: n, doing: "judging", next: "judges" });
  const l = pitchLists(nodes);
  return { rows: [...l.judged.map((n) => row(n, true, false)), ...l.judging.filter((n) => (n.pitch?.state || n.state) === "judging").map((n) => row(n, false, true))],
    raw: l.raw.filter((n) => n.queue !== "hold").map((n) => row(n, false, false)) };
}

/** *Judge now · 2 new pitches* (the leader's button): the first new pitch it judges, and its tooltip. */
export function judgePower(raw, lead) {
  const first = raw[0];
  return { slug: first?.slug || "", off: !first, words: first ? plural(raw.length, "new pitch", "new pitches") : "no new pitch",
    tip: first ? `${lead} and the four views judge “${first.title}” now` : "No new pitch to judge" };
}

/** The parties a pitch may be sent to (§5): the project's, but General and Ideation's, in the Board's order; a preset the decision names that the project
 *  lacks comes last, `preset: true` (Send opens New party with it). [{slug, name, preset}] */
export function sendTargets(map, decision) {
  const out = goalList().filter((g) => !isIdeation(map, g.slug)).map((g) => ({ slug: g.slug, name: g.title, preset: false }));
  const w = decision?.where;
  if (w?.party && w.preset && !out.some((x) => x.slug === w.party)) out.push({ slug: w.party, name: w.name || w.party, preset: true });
  return out;
}

/** The party Send starts on: the decision's, else the first of the project's. */
export const sendDefault = (targets, decision) => (targets.find((x) => x.slug === decision?.where?.party) || targets.find((x) => !x.preset) || targets[0])?.slug || "";
