// Today (docs/specs/49-one-window.md §7): the strip on the left is the day of the party shown — a mark per event, newest at the top
// (a check in the success ink, a cross in danger, a flag for a goal in main, the host's own marks muted or in ink), a clock over them. Each is a button whose label says *HH:MM · title · words*;
// a click opens what the event is about in the drawer.
import { html, cls } from "../html.js";
import { Icon, Sign } from "../orkui.js";
import { todayData, showResult, showTask, showIdea, showGoal, showGate } from "../shell/store.js";
import { TODAY_TONE, todayOf, todayTip } from "./arenawords.js";

function open(e) {
  const o = e.open || {}, via = { via: "today" };
  if (o.kind === "result") showResult(o.slug, o.task, via);
  else if (o.kind === "task") showTask(o.slug, o.task, via);
  else if (o.kind === "goal") showGoal(o.slug, via);
  else if (o.kind === "gate") showGate(via);
  else showIdea(o.slug, via);
}

const SIGNS = { "✓": "check", "✗": "cross", "⚑": "flag" };           // the host's marks that orkUI draws as signs (spec 50 §1.6)

export function TodayStrip({ goal }) {
  const rows = todayOf(todayData.value, goal);
  return html`<nav class="arena-today" aria-label="Today">
    <span class="arena-today__clock"><${Icon} name="clock" /></span>
    ${rows.map((e, i) => html`<button type="button" key=${i} class=${cls("arena-hitem", TODAY_TONE[e.tone] || "")} title=${todayTip(e)} aria-label=${todayTip(e)} data-open=${e.open?.kind}
      onClick=${() => open(e)}>${SIGNS[e.mark] ? html`<${Sign} name=${SIGNS[e.mark]} />` : e.mark}</button>`)}
  </nav>`;
}
