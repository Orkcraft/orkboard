// The party (docs/specs/49-one-window.md §5.1–§5.3): a member is a small framed card — its head, its two numbers (runs and redos,
// its price for a run), its name between two marks (the tool it runs on, its level), its state and what it does now. Hovering or
// focusing it shows its whole face beside it (the peek); a click shows only its work (solo).
import { useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head, Icon, TIER_WORDS, ORKUI } from "../orkui.js";
import { agents, roles } from "../shell/store.js";
import { solo } from "./arenastate.js";
import { useLit } from "./motion.js";
import { BAND_WORDS, BAND_KEYWORD, columnOf, nowOf, statsOf, roleOf, memberView, raceOf, signOf } from "./arenawords.js";

const MARKS = `${ORKUI}/marks`;
/** One of orkUI's marks (a tool's, a level's) at 16 × 16 from the @2x image, pixelated; its word is its tooltip. */
function Mark({ name, tip, where = "" }) {
  return html`<img class=${`ork-mark${where ? ` arena-mark--${where}` : ""}`} src=${`${MARKS}/${name}.png`} srcset=${`${MARKS}/${name}@2x.png 2x`} alt="" title=${tip} draggable="false" />`;
}

/** The peek: a larger card, nothing in it pressable (`aria-hidden`): the price in a gem, the head, who it is, its state, now and next, what it takes. */
function Peek({ m, st, line, role, view, lead, side, nodes }) {
  const mine = (role?.chips || []).filter((c) => c.state === "running" || c.state === "testing").length;
  const model = (() => {
    const label = (roles.value?.models || []).find((x) => x.id === (role?.model || ""))?.label || "", named = /\(([^)]+)\)/.exec(label);
    return named ? named[1] : TIER_WORDS[role?.model] ? "" : role?.model || "";
  })();
  const takes = lead ? "plans its ideas and accepts the goal"
    : m.band === "check" ? (roles.value?.library || []).find((a) => a.id === m.slug)?.check?.applies || "every idea of the goal"
    : (role?.kinds || []).join(", ") || "any task";
  const who = [raceOf(m.head), st.harness.name, st.level, model, lead ? "" : `${mine} of ${role?.max_parallel ?? 1} at once`].filter(Boolean).join(" · ");
  return html`<div class=${cls("arena-peek", { "is-side": side })} aria-hidden="true">
    <span class=${cls("ork-frame arena-pcard", { alert: m.state === "needs" })}>
      <span class="arena-pcard__top"><span class="ork-gem" title=${st.priceTip}>${st.price}</span><span class="arena-cap">${lead ? "a plan" : "a run"}</span>
        <span class="arena-band">${BAND_WORDS[m.band]}</span></span>
      <span class="arena-art">${m.head && html`<${Head} race=${m.head.race} tier=${m.head.tier} size="mid" />`}</span>
      <span class="arena-banner">${m.name}</span>
      <span class="arena-typeline">${who}</span>
      <span class="arena-pcard__box"><span class=${cls("arena-pcard__state", view.tone)}>${view.words}${m.state === "work" ? " ↻" : ""}</span>
        <span class="arena-pcard__line">${line.now}</span><span class="arena-pcard__line is-muted">${line.next}</span>
        <span class="arena-pcard__rule"><b>${BAND_KEYWORD[m.band]}</b> ${takes}</span></span>
      <span class="arena-pcard__caps"><span class="arena-cap">${st.runsWord}</span></span>
      <span class="arena-pcard__foot"><span class="ork-stat" title=${st.runsTip}>${st.runs}</span><span class="arena-spacer"></span>
        <span class="ork-stat" title=${st.priceTip}>${st.price}</span></span>
    </span>
  </div>`;
}

/** A member of the party row, or the leader: a small framed row. Its head wears three signs on its corners, half over it — its level's chevrons
 *  top left, the tool it runs on bottom left, its state top right (✗ a failure, ! another stop, ↻ at work, a moon tonight; none when next or free) —
 *  and beside it three short lines: its name, its runs and redos, its price for a run. The words of all that are in the peek and the label. */
export function Member({ m, nodes, planning, lead = false }) {
  const role = roleOf(agents.value, m.slug), st = statsOf(m, role, lead);
  const col = lead ? [] : columnOf(m, nodes), line = nowOf(m, col, planning, lead);
  const view = memberView(m, st, line, raceOf(m.head)), sign = signOf(m);
  const on = solo.value === m.slug, dim = !!solo.value && !on;
  const pick = () => { solo.value = on ? "" : m.slug; };
  const runs = useRef();
  useLit(runs, st.runs);                                   // a merge lights the first number once (§11)
  return html`<div class="arena-mcol" data-agent=${m.slug}>
    <button type="button" class=${cls("arena-member", { "is-on": on, "is-dim": dim, "is-lead": lead })} data-state=${m.state} data-agent=${m.slug}
      aria-pressed=${on} aria-label=${view.label} onClick=${pick}>
      <span class="arena-tport">${m.head && html`<${Head} race=${m.head.race} tier=${m.head.tier} size="mid" />`}
        <${Mark} name=${`rank-${st.rank}`} tip=${st.rankTip} where="r" /><${Mark} name=${`harness-${st.harness.id}`} tip=${st.harnessTip} where="h" />
        ${sign && html`<span class=${cls("arena-sign", sign.tone)} title=${view.words} data-sign=${sign.mark || "moon"}>${sign.mark || html`<${Icon} name="moon" />`}</span>`}</span>
      <span class="arena-tbody"><span class="arena-member__nm">${m.name}</span>
        <span class="arena-num" ref=${runs} title=${st.runsTip}>${st.runs}</span><span class="arena-num is-muted" title=${st.priceTip}>${st.price}</span></span>
    </button>
    <${Peek} m=${m} st=${st} line=${line} role=${role} view=${view} lead=${lead} side=${lead} nodes=${nodes} />
  </div>`;
}

/** The party row (§5.1): the builders, then the checkers, each under its column. */
export function PartyRow({ g, members, nodes, planning, cols }) {
  return html`<section class="arena-team" aria-label="Party" style=${`--cols:${cols}`}>
    ${members.map((m) => html`<${Member} key=${m.slug} m=${m} nodes=${nodes} planning=${planning} />`)}
  </section>`;
}
