// The one window (docs/specs/49-one-window.md, docs/specs/50-parties-and-goals.md, docs/specs/52-goal-types.md, docs/specs/69-parties-in-the-column.md, decisions §62, §63, §65, §84): the day's strip, the
// column of the parties (partylist.js: the project's line, a heading for each party, the open party's leader and goals under its heading with the filter and the New goal pile), and the party's field — the party line, the party row with the gate, the members' tasks in
// rows by phase as stacks of cards running down from them with the results beside them, what waits for you and the limits along the bottom. The drawer
// (shell.js) slides over it. All of it reads `ideas.map`, `ideas.board`, `ideas.agents`, `ideas.gate`, `ideas.today`, `ideas.flags` and the snapshot; its
// commands are the Board's own. Ideation's field is its pitches by state across the party's columns (pitches.js, docs/specs/65-ideation.md §8).
import { useEffect, useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { track, board, OPS } from "../board/store.js";
import { Operations } from "../board/ops.js";
import { flagsData, lookTick, mapData } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { town } from "../link.js";
import { solo, narrow, picks, shownGoals } from "./arenastate.js";
import { goalsOf, handOf, nodesOf, partyOf, planningOf, resultsOf } from "./arenawords.js";
import { inFilter } from "./goalwords.js";
import { shownOf } from "./goaltabs.js";
import { PartyList } from "./partylist.js";
import { goalList } from "../board/store.js";
import { TodayStrip } from "./todaystrip.js";
import { Left } from "./goals.js";
import { FlagLine, PartyLine } from "./partyline.js";
import { Columns, Solo } from "./field.js";
import { Spread } from "./spread.js";
import { Arrows } from "./arrows.js";
import { Looks } from "./waits.js";
import { PartyRow } from "./members.js";
import { GateBox } from "./gate.js";
import { Stops } from "./stops.js";
import { Limits } from "./limits.js";
import { Cards } from "../board/cards.js";
import { closeFlagLine, seeFlags } from "./flags.js";
import { PitchField } from "./pitches.js";
import { pitchPlanning } from "./pitchwords.js";

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

/** A stop of the project (spec 54 §2.1): the goal it is about is one its party's filter shows (a stop about the party itself, no goal, stays). The party shown has the
 *  filter and the goal peeked; another party has only its picks. */
const stopIn = (shown, s) => {
  const goal = s.node?.slug || s.row?.idea || "";
  return !goal || inFilter(shown, goal);
};
const keepOf = (shownSlug) => (party, s) => stopIn(party === shownSlug ? shownGoals(party) : picks.value[party] || [], s);

/** The one hand: every stop of the project, the most urgent first (`Stops` lays it out from the middle). */
const handFor = (m, shown, withResults) => handOf({ map: m, needs: board.value?.needs_you || [], order: goalList().map((x) => x.slug), shown, keep: keepOf(shown), withResults,
  ops: town.value?.ops_rev !== undefined });

/** Operations' own field: the column's list (Operations open), its list, with the stops of the project along the bottom. */
function OpsField({ m }) {
  return html`<div class="arena arena-ops">
    <${PartyList} />
    <div class="arena-ops__main">
      <section class="arena-ops__body" aria-label="The party at work"><${Operations} withNew=${true} /></section>
      <div class="arena-stops"><${Stops} stops=${handFor(m, OPS, false)} /><${Limits} /></div>
    </div>
  </div>`;
}

/** The party shown, in full. Keyed by the party so that what was picked or drawn on the last one does not carry over. */
function Party({ m, g }) {
  const nodes = nodesOf(m, g.slug), { lead, members } = partyOf(g, nodes), body = useRef();
  const pitch = !!g.ideation;                            // Ideation: pitches by state, no tasks (spec 65 §8)
  const planning = pitch ? pitchPlanning(nodes) : planningOf(g, nodes, lead?.name || g.leader?.name);
  const shown = shownGoals(g.slug), results = resultsOf(nodes);
  const wide = !narrow.value;
  const cols = members.map(() => (wide ? "minmax(0,1fr)" : "minmax(150px,1fr)")).join(" ") || "minmax(0,1fr)";
  const reading = planning.rows.find((r) => r.busy)?.full || "";
  const all = handFor(m, g.slug, !wide);                 // below 1 024 px the party shown's results join the bottom row (§3)
  return html`<div class=${cls("arena", { "is-narrow": narrow.value, "is-ideation": pitch })} data-goal=${g.slug}>
    ${wide && html`<${TodayStrip} goal=${g.slug} />`}
    <${PartyList} body=${html`<${Left} g=${g} nodes=${nodes} planning=${planning} lead=${lead} />`} />
    <div class="arena-field">
      <div class="arena-top"><${PartyLine} g=${g} nodes=${nodes} lead=${lead?.name || "Taskmaster"} reading=${reading} doing=${pitch ? "judging" : "reading"} /><${FlagLine} /></div>
      <div class="arena-play">
        <${PartyRow} g=${g} members=${members} nodes=${nodes} planning=${planning} cols=${cols} />
        <section class="arena-body" aria-label="The party at work" ref=${body}>
          ${!wide && html`<div class="arena-cards"><${Cards} /></div>`}
          ${pitch ? html`<${PitchField} g=${g} members=${members} nodes=${nodes} cols=${cols} />`
            : solo.value ? html`<${Solo} g=${g} members=${members} lead=${lead} nodes=${nodes} planning=${planning} shown=${shown} />`
            : html`<${Columns} g=${g} members=${members} nodes=${nodes} cols=${cols} shown=${shown} />`}
          ${!pitch && html`<${Spread} members=${members} nodes=${nodes} />`}
          ${!pitch && html`<${Arrows} host=${body} nodes=${nodes} />`}
        </section>
      </div>
      ${wide && html`<${Looks} g=${g} results=${results} nodes=${nodes} shown=${shown} />`}
      <div class="arena-gatebox"><${GateBox} /></div>
      <div class="arena-stops"><${Stops} stops=${all} /><${Limits} /></div>
    </div>
  </div>`;
}

export function Arena() {
  useNarrow();
  const m = mapData.value, flags = flagsData.value;
  useEffect(() => { seeFlags(flags?.goals); }, [flags]);                           // a goal's flag is said once per device (spec 50 §3.8)
  useEffect(() => { closeFlagLine(); }, [lookTick.value]);                           // another project: nothing of the last one's line stays
  if (!m) return html`<p class="ok-tone-muted arena-note">Reading the board…</p>`;
  const parties = goalsOf(m, goalList().map((x) => x.slug)), want = shownOf(parties, track.value);
  if (want === OPS) return html`<${OpsField} m=${m} />`;
  const g = parties.find((x) => x.slug === want);
  if (!g && want) return html`<p class="ok-tone-muted arena-note">Reading the board…</p>`;           // a party just saved: the Map has it in a moment
  if (!g) {
    const ops = town.value?.ops_rev !== undefined;                                    // no party, but Operations' stops still wait in the one hand
    return html`<div class="arena arena-ops"><${PartyList} /><div class="arena-ops__main"><div class="shell-empty arena-note"><p>No parties yet</p>
      <p><button class="ork-btn primary" onClick=${() => openDialog("goal")}>New party</button>
        <button class="ork-btn" title="A goal needs a party: this makes one first" onClick=${() => openDialog("goal", { then: "idea" })}>New goal</button></p></div>
      ${ops && html`<div class="arena-stops"><${Stops} stops=${handFor(m, "", false)} /><${Limits} /></div>`}</div></div>`;
  }
  return html`<${Party} key=${g.slug} m=${m} g=${g} />`;
}
