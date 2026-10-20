// The cards at the top of the Map (docs/specs/42-coming-back.md §1.4): *While you were away*, what the Board did since this
// device's last look (js/shell/look.js). An `.ork-card` with its head in the pixel face and its lines in the text face, each only
// when it has something to say; it covers nothing (no backdrop, no dialog) and one press closes it. A view of what the Board
// holds: its links open an idea, a goal or Needs you, and change nothing.
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { cards, closeCard } from "../shell/look.js";
import { showIdea, showGoal, showNeeds, logOpened } from "../shell/store.js";
import { Modal, closeDialog, openDialog } from "../shell/modals.js";
import { ask, goalList, track } from "./store.js";

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

/** A list of links with commas between them. */
const joined = (items, sep = ", ") => items.map((x, i) => html`${i ? sep : ""}${x}`);

function Recap({ r }) {
  const m = r.merged || { tasks: 0, first_time: 0, ideas: [] };
  const link = (i, via = "recap") => html`<button key=${i.slug} type="button" class="board-link" onClick=${() => showIdea(i.slug, { via })}>${i.short}</button>`;
  const flagLine = (f) => html`<p class="away__flag">${f.met ? "Flag raised: " : ""}<button type="button" class="board-link" onClick=${() => showGoal(f.goal, { via: "recap" })}>${f.short}</button>${f.met ? ", met" : ": not met yet"}, says ${f.by}</p>`;
  return html`<div class="away__lines">
    ${m.tasks > 0 && html`<p class="away__merged">${resultsWords(m, r.into || "dev")}</p>
      ${m.ideas.length > 0 && html`<p class="away__ideas">${joined(m.ideas.slice(0, SHOWN).map((i) => html`${link(i)}${i.done ? " · done" : ""}`))}${m.ideas.length > SHOWN ? ` and ${m.ideas.length - SHOWN} more` : ""}</p>`}`}
    ${(r.flags || []).map((f) => html`<div key=${f.goal}>${flagLine(f)}</div>`)}
    ${r.night && html`<p class="away__night">${nightWords(r.night)}</p>`}
    ${(r.proposed || []).length > 0 && html`<p class="away__proposed">Proposed for you: ${joined(r.proposed.map((i) => html`<button key=${i.slug} type="button" class="board-link" onClick=${showNeeds}>${i.short}</button>`))}</p>`}
    ${(r.failed || []).length > 0 && html`<p class="away__failed ok-tone-error">Failed: ${joined(r.failed.map((f) => html`<button key=${f.slug + f.task} type="button" class="board-link" onClick=${() => showIdea(f.slug, { via: "recap" })}>${f.short} · ${f.task}</button>`), "; ")}</p>`}
    ${r.usd > 0 && html`<p class="away__usd ok-tone-muted">${usdWords(r.usd)}</p>`}
    <p class="away__waits"><button type="button" class="board-link" onClick=${showNeeds}>${waitsWords(r.waits || { you: 0, review: 0 })}</button></p>
  </div>`;
}

/** The first card waiting, or nothing. */
export function Cards() {
  const c = cards.value[0];
  if (!c) return null;
  const label = "While you were away";
  return html`<section class="ork-card away" aria-label=${label} data-card=${c.kind}
      onKeyDown=${(e) => { if (e.key === "Escape") { e.stopPropagation(); closeCard(); } }}>
    <header class="away__head"><h3 class="away__title">${label} · ${awayWords(c.data.hours)}</h3></header>
    <${Recap} r=${c.data} />
    <footer class="away__foot"><button type="button" class="ork-btn quiet" onClick=${closeCard}>Close</button></footer>
  </section>`;
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

/** This week (spec 42 §6): the work of the last seven days, at API prices, beside today's spend. Reads `ideas.week_work` when opened. */
export function WeekDialog() {
  const [w, setW] = useState(null);
  useEffect(() => { ask("ideas.week_work").then((got) => { if (got) setW(got); }); logOpened("week", "this"); }, []);
  const newIdea = () => { closeDialog(); if (goalList().length) openDialog("idea", track.value ? { goal: track.value } : {}); else openDialog("goal", { then: "idea" }); };
  return html`<${Modal} title="This week" onClose=${closeDialog} foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Close</button>`}>
    ${!w ? html`<p class="ok-tone-muted">Reading the week…</p>` : html`<div class="week">
      ${weekMoney(w) && html`<p class="week__usd">${weekMoney(w)}</p>`}
      <p class="week__results">${weekResults(w)}</p>
      ${weekNights(w.nights) && html`<p class="week__nights">${weekNights(w.nights)}</p>`}
      ${w.night_on && (w.tonight > 0 ? html`<p class="week__tonight">Tonight: ${w.tonight} wait</p>`
        : html`<p class="week__tonight">Nothing waits for tonight · <button type="button" class="board-link" onClick=${newIdea}>New idea</button></p>`)}
    </div>`}
  <//>`;
}
