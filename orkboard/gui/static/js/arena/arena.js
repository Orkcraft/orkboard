// The one window (docs/specs/49-one-window.md): under the goal tabs, the day's strip, Planning over the leader, and the goal's field —
// the ideas bar, the party's columns with the results beside them, the party row with the gate, what waits for you and the limits along
// the bottom. The drawer (shell.js) slides over it. All of it reads `ideas.map`, `ideas.board`, `ideas.agents`, `ideas.gate`,
// `ideas.today` and the snapshot; its commands are the Board's own.
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { track, board, OPS } from "../board/store.js";
import { Operations } from "../board/ops.js";
import { mapData } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { solo, narrow } from "./arenastate.js";
import { goalsOf, nodesOf, opStopsOf, partyOf, planningOf, resultStop, resultsOf, stopsOf } from "./arenawords.js";
import { shownOf } from "./goaltabs.js";
import { goalList } from "../board/store.js";
import { TodayStrip } from "./todaystrip.js";
import { Planning } from "./planning.js";
import { IdeasBar } from "./ideabar.js";
import { Columns, Solo } from "./field.js";
import { Looks } from "./waits.js";
import { PartyRow } from "./members.js";
import { GateBox } from "./gate.js";
import { Stops } from "./stops.js";
import { Limits } from "./limits.js";

const NARROW = "(max-width: 1023px)";

/** Below 1 024 px (§3): the strip is gone, the left column is narrower, the results join the bottom row, the columns scroll sideways. */
function useNarrow() {
  useEffect(() => {
    const m = matchMedia(NARROW), on = () => { narrow.value = m.matches; };
    on();
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
}

/** Operations' own field: its list, with the rows that wait for the person along the bottom. */
function OpsField() {
  const stops = opStopsOf(board.value?.needs_you || []);
  return html`<div class="arena arena-ops">
    <section class="arena-ops__body" aria-label="The goal at work"><${Operations} withNew=${true} /></section>
    <div class="arena-stops"><${Stops} g=${null} stops=${stops} /><${Limits} /></div>
  </div>`;
}

/** The goal shown, in full. Keyed by the goal so that what was picked or drawn on the last one does not carry over. */
function Goal({ m, g }) {
  const nodes = nodesOf(m, g.slug), { lead, members } = partyOf(g, nodes);
  const planning = planningOf(g, nodes, lead?.name || g.leader?.name);
  const results = resultsOf(nodes), stops = stopsOf(board.value?.needs_you || [], g, nodes);
  const wide = !narrow.value;
  const cols = members.map((x) => (x.free ? "88px" : wide ? "minmax(0,1fr)" : "minmax(150px,1fr)")).join(" ");
  const reading = planning.rows.find((r) => r.busy)?.full || "";
  const all = wide ? stops : [...stops, ...results.map((r) => resultStop(r, nodes))];                 // below 1 024 px the results join the bottom row (§3)
  return html`<div class=${cls("arena", { "is-narrow": narrow.value })} data-goal=${g.slug}>
    ${wide && html`<${TodayStrip} goal=${g.slug} />`}
    <${Planning} g=${g} nodes=${nodes} planning=${planning} lead=${lead} />
    <section class="arena-field" aria-label="The goal at work">
      <${IdeasBar} g=${g} nodes=${nodes} lead=${lead?.name || "Taskmaster"} reading=${reading} />
      <div class="arena-play">
        ${solo.value ? html`<${Solo} g=${g} members=${members} lead=${lead} nodes=${nodes} planning=${planning} />` : html`<${Columns} g=${g} members=${members} nodes=${nodes} cols=${cols} />`}
        <${PartyRow} g=${g} members=${members} nodes=${nodes} planning=${planning} cols=${cols} />
      </div>
      ${wide && html`<${Looks} g=${g} results=${results} nodes=${nodes} />`}
      <div class="arena-gatebox"><${GateBox} /></div>
      <div class="arena-stops"><${Stops} g=${g} stops=${all} /><${Limits} /></div>
    </section>
  </div>`;
}

export function Arena() {
  useNarrow();
  const m = mapData.value;
  if (!m) return html`<p class="ok-tone-muted arena-note">Reading the board…</p>`;
  const goals = goalsOf(m, goalList().map((x) => x.slug)), want = shownOf(goals, track.value);
  if (want === OPS) return html`<${OpsField} />`;
  const g = goals.find((x) => x.slug === want);
  if (!g) return html`<div class="shell-empty arena-note"><p>No goals yet</p><p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New goal</button></p></div>`;
  return html`<${Goal} key=${g.slug} m=${m} g=${g} />`;
}
