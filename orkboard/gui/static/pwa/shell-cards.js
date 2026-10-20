// The cards at the top of the Board tab (docs/specs/42-coming-back.md §1.4): *While you were away*, what the Board did since
// this phone's last look (board.js). An `.ork-card` with its head in the pixel face and its lines in the text face, each only when it
// has something to say; it covers nothing and one press closes it. Its links open an idea, a goal or Needs you and change nothing.
import { h, sheet } from "./util.js";
import { weekPaceWords, lastUnusedWords } from "./shell-words.js";

const SHOWN = 5;                                     // ideas named under the results, then *and 3 more*
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** "9 h", or "2 days" from 48 hours. */
export const awayWords = (hours) => (hours >= 48 ? `${Math.floor(hours / 24)} days` : `${hours} h`);

/** *5 results in dev, 4 the first time* · *1 result in dev, the first time* · *1 result in dev*. */
export function resultsWords(m, into) {
  const n = m.tasks, f = m.first_time;
  if (n === 1) return `1 result in ${into}${f ? ", the first time" : ""}`;
  return `${n} results in ${into}${f ? `, ${f} the first time` : ""}`;
}

/** *The night: drafted 2 ideas, started 1 plan, read 1 goal again, proposed 2 ideas*: only the parts above 0. */
export function nightWords(night) {
  const parts = [night.drafted && `drafted ${plural(night.drafted, "idea", "ideas")}`, night.started && `started ${plural(night.started, "plan", "plans")}`,
    night.refreshed && `read ${plural(night.refreshed, "goal", "goals")} again`, night.proposed && `proposed ${plural(night.proposed, "idea", "ideas")}`].filter(Boolean);
  return parts.length ? `The night: ${parts.join(", ")}` : "";
}

/** *Waits for you: 1 answer, 3 results to check*, else *Nothing waits for you*. */
export function waitsWords(w) {
  const parts = [w.you && plural(w.you, "answer", "answers"), w.review && plural(w.review, "result to check", "results to check")].filter(Boolean);
  return parts.length ? `Waits for you: ${parts.join(", ")}` : "Nothing waits for you";
}

/** *≈$4.20 of work at API prices, not your bill.* */
export const usdWords = (usd) => `≈$${usd.toFixed(2)} of work at API prices, not your bill.`;

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** "12–18 October", or "28 September–4 October" across a month. */
export function rangeWords(from, to) {
  const [, m1, d1] = from.split("-").map(Number), [, m2, d2] = to.split("-").map(Number);
  return m1 === m2 ? `${d1}–${d2} ${MONTHS[m2 - 1]}` : `${d1} ${MONTHS[m1 - 1]}–${d2} ${MONTHS[m2 - 1]}`;
}

/** 42 min · 3 h (from 2 hours) · 2 days (from 48 hours). */
export function durationWords(minutes) {
  if (minutes < 120) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return hours < 48 ? `${hours} h` : `${Math.floor(hours / 24)} days`;
}

const dollars = (usd) => `≈$${usd < 10 ? usd.toFixed(2).replace(/\.00$/, "") : Math.round(usd)}`;

/** The ISO week (`2026-W42`) of a date. */
export function isoWeek(date) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const year = d.getUTCFullYear();
  return `${year}-W${String(Math.ceil(((d - Date.UTC(year, 0, 1)) / 86400000 + 1) / 7)).padStart(2, "0")}`;
}

/** Last week's card ahead of the others (the recap's comes after it); `via`: where it was asked from (the drawer's row says "map"). */
export function pushWeek(core, data, via = "") {
  core.st.cards = [{ kind: "week", data }, ...core.st.cards.filter((c) => c.kind !== "week")];
  core.call("ideas.log", { event: "opened", what: "week", ref: data.week, device: "phone", ...(via ? { via } : {}) });
  core.draw();
}

/** `core`: the board's frame (open, go, draw). Returns {section(card), close()}. */
export function makeCards(core) {
  const st = core.st;
  const close = () => { st.cards = st.cards.slice(1); core.draw(); };
  const link = (text, run) => h("button", { class: "linkish", type: "button", onclick: run }, text);
  const idea = (i) => link(i.short, () => core.open({ kind: "idea", slug: i.slug }, "recap"));
  const goal = (g) => link(g.short, () => core.open({ kind: "goal", slug: g.goal }, "recap"));
  const needs = (text) => link(text, () => core.go("needs"));
  const joined = (nodes, sep = ", ") => nodes.flatMap((n, i) => (i ? [sep, n] : [n]));

  function recap(r) {
    const m = r.merged || { tasks: 0, first_time: 0, ideas: [] };
    const lines = [];
    if (m.tasks > 0) {
      lines.push(h("p", { class: "away-merged" }, resultsWords(m, r.into || "dev")));
      if ((m.ideas || []).length) {
        lines.push(h("p", { class: "away-ideas" }, ...joined(m.ideas.slice(0, SHOWN).map((i) => h("span", {}, idea(i), i.done ? " · done" : ""))),
          m.ideas.length > SHOWN ? ` and ${m.ideas.length - SHOWN} more` : ""));
      }
    }
    for (const f of r.flags || []) {
      lines.push(h("p", { class: "away-flag" }, f.met ? "Flag raised: " : "", goal(f), f.met ? ", met" : ": not met yet", `, says ${f.by}`));
    }
    if (r.night && nightWords(r.night)) lines.push(h("p", { class: "away-night" }, nightWords(r.night)));
    if ((r.proposed || []).length) lines.push(h("p", { class: "away-proposed" }, "Proposed for you: ", ...joined(r.proposed.map((i) => needs(i.short)))));
    if ((r.failed || []).length) {
      lines.push(h("p", { class: "away-failed" }, "Failed: ", ...joined(r.failed.map((f) => link(`${f.short} · ${f.task}`,
        () => core.open({ kind: "idea", slug: f.slug }, "recap"))), "; ")));
    }
    if (r.usd > 0) lines.push(h("p", { class: "away-usd muted" }, usdWords(r.usd)));
    if (r.nights >= 2) lines.push(h("p", { class: "away-streak" }, `${r.nights} nights in a row with work done.`));
    lines.push(h("p", { class: "away-waits" }, needs(waitsWords(r.waits || { you: 0, review: 0 }))));
    return lines;
  }

  const goalLink = (f, text) => link(text, () => core.open({ kind: "goal", slug: f.goal }, "week"));
  const ideaLink = (i, text) => link(text, () => core.open({ kind: "idea", slug: i.slug }, "week"));

  /** Last week's lines (spec 42 §7.2), each only when it has something to say. */
  function week(w) {
    const into = w.into || "dev", pct = (a) => `${Math.round((a.first_time / a.merged) * 100)} %`;
    const lines = [];
    if (w.merged > 0) {
      const sure = w.first_time ? `${pct(w)}${w.before ? `; the week before ${pct(w.before)}` : ""}` : "";
      lines.push(h("p", { class: "away-merged" }, `${resultsWords({ tasks: w.merged, first_time: w.first_time }, into)}${sure ? ` (${sure})` : ""}`));
    }
    if (w.usd_per_merged != null) {
      lines.push(h("p", { class: "away-usd" }, `${dollars(w.usd_per_merged)} a result${w.before?.usd_per_merged != null ? ` (the week before ${dollars(w.before.usd_per_merged)})` : ""}`));
    }
    if ((w.goals || []).length) {
      lines.push(h("p", { class: "away-goals" }, "Goals: ", ...joined(w.goals.map((g, n) => h("span", {}, goalLink(g, g.short), n === 0 ? `, ${g.done} ${g.done === 1 ? "idea" : "ideas"} done` : `, ${g.done}`)), " · ")));
    }
    if ((w.flags || []).length) {
      lines.push(h("p", { class: "away-flag" }, "Flags: ", ...joined(w.flags.map((f) => h("span", {}, goalLink(f, f.short), f.met ? ", met" : ", not met yet")), "; ")));
    }
    const extremes = [w.dearest && h("span", {}, "Cost the most: ", ideaLink(w.dearest, w.dearest.short), `, ${dollars(w.dearest.usd)}`),
      w.fastest && h("span", {}, `Fastest from idea to ${into}: `, ideaLink(w.fastest, w.fastest.short), `, ${durationWords(w.fastest.minutes)}`)].filter(Boolean);
    if (extremes.length) lines.push(h("p", { class: "away-extremes" }, ...joined(extremes, " · ")));
    if (w.answers) {
      const left = w.answers.decided ? `; ${w.answers.decided} ${w.answers.decided === 1 ? "card" : "cards"} left to the Taskmaster` : "";
      lines.push(h("p", { class: "away-answers" }, `Questions: ${w.answers.recommended} of ${w.answers.answers} answers were the recommended one${left}`));
    }
    const nights = weekNights(w.nights);
    if (nights) lines.push(h("p", { class: "away-nights" }, `${nights.replace("The last 7 nights", "Nights")}${w.streak >= 2 ? ` · ${w.streak} in a row` : ""}`));
    return lines.length ? lines : [h("p", { class: "muted" }, "Nothing was merged or finished.")];
  }

  /** The card for the first one waiting; null when none. */
  function section(card) {
    if (!card) return null;
    const isWeek = card.kind === "week";
    const label = isWeek ? "Last week" : "While you were away";
    const el = h("section", { class: "ork-card away", "aria-label": label, "data-card": card.kind },
      h("header", { class: "away-head" }, h("h3", {}, isWeek ? `${label} · ${rangeWords(card.data.from, card.data.to)}` : `${label} · ${awayWords(card.data.hours)}`)),
      h("div", { class: "away-lines" }, ...(isWeek ? week(card.data) : recap(card.data))),
      h("footer", { class: "away-foot" }, h("button", { class: "ork-btn quiet", type: "button", onclick: close }, "Close")));
    el.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.stopPropagation(); close(); } });
    return el;
  }

  return { section, close };
}

/** *≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill*: a part that is null (or nothing) is left out. */
export function weekMoney(w) {
  const dollars = (usd) => `≈$${usd < 1 ? usd.toFixed(2) : Math.round(usd)}`;
  const mine = w.usd > 0 ? w.usd : 0, ops = w.ops_usd > 0 ? w.ops_usd : 0;
  if (!mine && !ops) return "";
  if (mine && ops) return `${dollars(mine)} of work at API prices in this project, ${dollars(ops)} in Operations: not your bill`;
  return `${dollars(mine || ops)} of work at API prices in ${mine ? "this project" : "Operations"}: not your bill`;
}

/** *12 results in dev, 10 the first time · ≈$3.84 a result*. */
export function weekResults(w) {
  if (!w.merged) return `No results in ${w.into || "dev"} in the last 7 days`;
  return `${resultsWords({ tasks: w.merged, first_time: w.first_time }, w.into || "dev")}${w.usd_per_merged != null ? ` · ≈$${w.usd_per_merged.toFixed(2)} a result` : ""}`;
}

/** *The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running*: parts at 0 left out. */
export function weekNights(n) {
  const parts = [n.worked && `${n.worked} with work done`, n.idle && `${n.idle} with none`, n.off && `${n.off} Orkline was not running`].filter(Boolean);
  return parts.length ? `The last 7 nights: ${parts.join(", ")}` : "";
}

/** The This week sheet (spec 42 §6), opened from the drawer's Spend today. `core`: the board's frame; `newIdea`: opens New idea. */
export function makeWeek(core, newIdea) {
  const body = h("div", { class: "week" }, h("p", { class: "muted" }, "Reading the week…"));
  const sh = sheet("This week", body);
  async function open() {
    body.replaceChildren(h("p", { class: "muted" }, "Reading the week…"));
    sh.open();
    core.call("ideas.log", { event: "opened", what: "week", ref: "this", device: "phone" });
    const w = await core.call("ideas.week_work");
    if (!w) return;
    const money = weekMoney(w), nights = weekNights(w.nights);
    body.replaceChildren(...[money ? h("p", { class: "week-usd" }, money) : null, h("p", { class: "week-results" }, weekResults(w)),
      nights ? h("p", { class: "week-nights" }, nights) : null,
      w.streak >= 2 ? h("p", { class: "week-streak" }, `${w.streak} nights in a row`) : null,
      w.night_on ? (w.tonight > 0 ? h("p", { class: "week-tonight" }, `Tonight: ${w.tonight} wait`)
        : h("p", { class: "week-tonight" }, "Nothing waits for tonight · ", h("button", { class: "linkish", type: "button", onclick: () => { sh.close(); newIdea(); } }, "New idea"))) : null,
      weekPaceWords(w) ? h("p", { class: "week-pace" }, weekPaceWords(w)) : null,
      w.week && lastUnusedWords(w) ? h("p", { class: "week-unused" }, lastUnusedWords(w)) : null].filter(Boolean));
  }
  return { el: sh.el, open };
}
