// The cards at the top of the Map (docs/specs/42-coming-back.md §1.4): *While you were away*, what the Board did since this
// device's last look (js/shell/look.js). An `.ork-card` with its head in the pixel face and its lines in the text face, each only
// when it has something to say; it covers nothing (no backdrop, no dialog) and one press closes it. A view of what the Board
// holds: its links open an idea, a goal or Needs you, and change nothing.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { Sign } from "../orkui.js";
import { cards, closeCard } from "../shell/look.js";
import { showIdea, showGoal, showNeeds, logOpened } from "../shell/store.js";
import { Modal, closeDialog, openDialog } from "../shell/modals.js";
import { ask, goalList, track } from "./store.js";
import { pctOf } from "../spend.js";

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

/** *The night: drafted 2 goals, started 1 plan, read 1 party again, proposed 2 goals*: only the parts above 0. */
export function nightWords(night) {
  const parts = [night.drafted && `drafted ${plural(night.drafted, "goal", "goals")}`, night.started && `started ${plural(night.started, "plan", "plans")}`,
    night.refreshed && `read ${plural(night.refreshed, "party", "parties")} again`, night.proposed && `proposed ${plural(night.proposed, "goal", "goals")}`].filter(Boolean);
  return parts.length ? `The night: ${parts.join(", ")}` : "";
}

/** *Waits for you: 1 answer, 3 results to check*, else *Nothing waits for you*. */
export function waitsWords(w) {
  const parts = [w.you && plural(w.you, "answer", "answers"), w.review && plural(w.review, "result to check", "results to check")].filter(Boolean);
  return parts.length ? `Waits for you: ${parts.join(", ")}` : "Nothing waits for you";
}

/** *≈$4.20 of work at API prices, not your bill.* */
export const usdWords = (usd) => (pctOf(usd) ? `≈${pctOf(usd)} of work, an estimate.` : `≈$${usd.toFixed(2)} of work at API prices, not your bill.`);

/** A list of links with commas between them. */
const joined = (items, sep = ", ") => items.map((x, i) => html`${i ? sep : ""}${x}`);

function Recap({ r }) {
  const m = r.merged || { tasks: 0, first_time: 0, ideas: [] };
  const link = (i, via = "recap") => html`<button key=${i.slug} type="button" class="board-link" onClick=${() => showIdea(i.slug, { via })}>${i.short}</button>`;
  const flagLine = (f) => (f.idea
    ? html`<p class="away__flag"><${Sign} name="flag" /> <button type="button" class="board-link" onClick=${() => showIdea(f.idea, { via: "recap" })}>${f.short}</button> is in main</p>`      // a goal's flag (spec 50 §2.4)
    : html`<p class="away__flag">${f.met ? "Flag raised: " : ""}<button type="button" class="board-link" onClick=${() => showGoal(f.goal, { via: "recap" })}>${f.short}</button>${f.met ? ", met" : ": not met yet"}, says ${f.by}</p>`);   // a party's old flag keeps its line
  return html`<div class="away__lines">
    ${m.tasks > 0 && html`<p class="away__merged">${resultsWords(m, r.into || "dev")}</p>
      ${m.ideas.length > 0 && html`<p class="away__ideas">${joined(m.ideas.slice(0, SHOWN).map((i) => html`${link(i)}${i.done ? " · done" : ""}`))}${m.ideas.length > SHOWN ? ` and ${m.ideas.length - SHOWN} more` : ""}</p>`}`}
    ${(r.flags || []).map((f) => html`<div key=${f.goal}>${flagLine(f)}</div>`)}
    ${r.night && html`<p class="away__night">${nightWords(r.night)}</p>`}
    ${(r.proposed || []).length > 0 && html`<p class="away__proposed">Proposed for you: ${joined(r.proposed.map((i) => html`<button key=${i.slug} type="button" class="board-link" onClick=${showNeeds}>${i.short}</button>`))}</p>`}
    ${(r.failed || []).length > 0 && html`<p class="away__failed ok-tone-error">Failed: ${joined(r.failed.map((f) => html`<button key=${f.slug + f.task} type="button" class="board-link" onClick=${() => showIdea(f.slug, { via: "recap" })}>${f.short} · ${f.task}</button>`), "; ")}</p>`}
    ${r.usd > 0 && html`<p class="away__usd ok-tone-muted">${usdWords(r.usd)}</p>`}
    ${r.nights >= 2 && html`<p class="away__streak">${r.nights} nights in a row with work done.</p>`}
    <p class="away__waits"><button type="button" class="board-link" onClick=${showNeeds}>${waitsWords(r.waits || { you: 0, review: 0 })}</button></p>
  </div>`;
}

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

const dollars = (usd) => `≈${pctOf(usd) || `$${usd < 10 ? usd.toFixed(2).replace(/\.00$/, "") : Math.round(usd)}`}`;

function Week({ w }) {
  const into = w.into || "dev", pct = (a, b) => `${Math.round((a.first_time / a.merged) * 100)} %`;
  const goalLink = (f, text) => html`<button type="button" class="board-link" onClick=${() => showGoal(f.goal, { via: "week" })}>${text}</button>`;
  const ideaLink = (i, text) => html`<button type="button" class="board-link" onClick=${() => showIdea(i.slug, { via: "week" })}>${text}</button>`;
  const lines = [];
  if (w.merged > 0) {
    const sure = w.first_time ? `${pct(w, w)}${w.before ? `; the week before ${pct(w.before, w.before)}` : ""}` : "";
    lines.push(html`<p class="away__merged">${resultsWords({ tasks: w.merged, first_time: w.first_time }, into)}${sure && ` (${sure})`}</p>`);
  }
  if (w.usd_per_merged != null) {
    lines.push(html`<p class="away__usd">${dollars(w.usd_per_merged)} a result${w.before?.usd_per_merged != null ? ` (the week before ${dollars(w.before.usd_per_merged)})` : ""}</p>`);
  }
  if ((w.goals || []).length) {
    lines.push(html`<p class="away__goals">Parties: ${joined(w.goals.map((g, n) => html`${goalLink(g, g.short)}${n === 0 ? `, ${g.done} ${g.done === 1 ? "goal" : "goals"} done` : `, ${g.done}`}`), " · ")}</p>`);
  }
  if ((w.flags || []).length) {
    lines.push(html`<p class="away__flag">Flags: ${joined(w.flags.map((f) => (f.idea ? html`<${Sign} name="flag" /> ${ideaLink({ slug: f.idea }, f.short)} is in main`
      : html`${goalLink(f, f.short)}${f.met ? ", met" : ", not met yet"}`)), "; ")}</p>`);
  }
  const speed = [w.dearest && html`Cost the most: ${ideaLink(w.dearest, w.dearest.short)}, ${dollars(w.dearest.usd)}`,
    w.fastest && html`Fastest from goal to ${into}: ${ideaLink(w.fastest, w.fastest.short)}, ${durationWords(w.fastest.minutes)}`].filter(Boolean);
  if (speed.length) lines.push(html`<p class="away__extremes">${joined(speed, " · ")}</p>`);
  if (w.answers) {
    const left = w.answers.decided ? `; ${w.answers.decided} ${w.answers.decided === 1 ? "card" : "cards"} left to the Taskmaster` : "";
    lines.push(html`<p class="away__answers">Questions: ${w.answers.recommended} of ${w.answers.answers} answers were the recommended one${left}</p>`);
  }
  const nights = weekNights(w.nights);
  if (nights) lines.push(html`<p class="away__nights">${nights.replace("The last 7 nights", "Nights")}${w.streak >= 2 ? ` · ${w.streak} in a row` : ""}</p>`);
  return html`<div class="away__lines">${lines.length ? lines : html`<p class="ok-tone-muted">Nothing was merged or finished.</p>`}</div>`;
}

/** The first card waiting, or nothing. */
export function Cards() {
  const c = cards.value[0];
  if (!c) return null;
  const week = c.kind === "week";
  const label = week ? "Last week" : "While you were away";
  return html`<section class="ork-card away" aria-label=${label} data-card=${c.kind}
      onKeyDown=${(e) => { if (e.key === "Escape") { e.stopPropagation(); closeCard(); } }}>
    <header class="away__head"><h3 class="away__title">${week ? `${label} · ${rangeWords(c.data.from, c.data.to)}` : `${label} · ${awayWords(c.data.hours)}`}</h3></header>
    ${week ? html`<${Week} w=${c.data} />` : html`<${Recap} r=${c.data} />`}
    <footer class="away__foot"><button type="button" class="ork-btn quiet" onClick=${closeCard}>Close</button></footer>
  </section>`;
}

/** *≈$46 of work at API prices in this project, ≈$3 in Operations: not your bill*: a part that is null (or nothing) is left out. */
export function weekMoney(w) {
  const dollars = (usd) => `≈$${usd < 1 ? usd.toFixed(2) : Math.round(usd)}`;
  const mine = w.usd > 0 ? w.usd : 0, ops = w.ops_usd > 0 ? w.ops_usd : 0;
  if (!mine && !ops) return "";
  if (pctOf(mine || ops)) return mine && ops ? `≈${pctOf(mine)} of work in this project, ≈${pctOf(ops)} in Operations: an estimate`
    : `≈${pctOf(mine || ops)} of work in ${mine ? "this project" : "Operations"}: an estimate`;
  if (mine && ops) return `${dollars(mine)} of work at API prices in this project, ${dollars(ops)} in Operations: not your bill`;
  return `${dollars(mine || ops)} of work at API prices in ${mine ? "this project" : "Operations"}: not your bill`;
}

/** *12 results in dev, 10 the first time · ≈$3.84 a result*. */
export function weekResults(w) {
  if (!w.merged) return `No results in ${w.into || "dev"} in the last 7 days`;
  return `${resultsWords({ tasks: w.merged, first_time: w.first_time }, w.into || "dev")}${w.usd_per_merged != null ? ` · ≈${pctOf(w.usd_per_merged) || `$${w.usd_per_merged.toFixed(2)}`} a result` : ""}`;
}

/** *The last 7 nights: 4 with work done, 2 with none, 1 Orkline was not running*: parts at 0 left out. */
export function weekNights(n) {
  const parts = [n.worked && `${n.worked} with work done`, n.idle && `${n.idle} with none`, n.off && `${n.off} Orkline was not running`].filter(Boolean);
  return parts.length ? `The last 7 nights: ${parts.join(", ")}` : "";
}

/** *The week: 55 % left with 2 days to go: Low work starts by day*; "" with no week read (spec 44 §5). */
export function weekPace(w) {
  if (!w?.week) return "";
  const { left, rest, pace } = w.week;
  const days = Math.max(1, Math.ceil(rest * 7 - 1e-9));
  const does = { ahead: "Low work starts by day", even: "Low work waits for the night", behind: "Low work waits until the week comes back" }[pace] || "";
  return `The week: ${Math.round(left * 100)} % left with ${days} ${days === 1 ? "day" : "days"} to go${does ? `: ${does}` : ""}`;
}

/** This week (spec 42 §6): the work of the last seven days, at API prices, beside today's spend. Reads `ideas.week_work` when opened. */
export function WeekDialog() {
  const [w, setW] = useState(null);
  useEffect(() => { ask("ideas.week_work").then((got) => { if (got) setW(got); }); logOpened("week", "this"); }, []);
  const newGoal = () => { closeDialog(); if (goalList().length) openDialog("idea", track.value ? { goal: track.value } : {}); else openDialog("goal", { then: "idea" }); };
  return html`<${Modal} title="This week" onClose=${closeDialog} foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Close</button>`}>
    ${!w ? html`<p class="ok-tone-muted">Reading the week…</p>` : html`<div class="week">
      ${weekMoney(w) && html`<p class="week__usd">${weekMoney(w)}</p>`}
      <p class="week__results">${weekResults(w)}</p>
      ${weekNights(w.nights) && html`<p class="week__nights">${weekNights(w.nights)}</p>`}
      ${weekPace(w) && html`<p class="week__pace">${weekPace(w)}</p>`}
      ${w.last_unused != null && html`<p class="week__unused">Last week ended with ${Math.round(w.last_unused * 100)} % unused</p>`}
      ${w.streak >= 2 && html`<p class="week__streak">${w.streak} nights in a row</p>`}
      ${w.night_on && (w.tonight > 0 ? html`<p class="week__tonight">Tonight: ${w.tonight} wait</p>`
        : html`<p class="week__tonight">Nothing waits for tonight · <button type="button" class="board-link" onClick=${newGoal}>New goal</button></p>`)}
    </div>`}
  <//>`;
}
