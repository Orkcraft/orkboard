// The party (docs/specs/49-one-window.md §5.1–§5.3): a member is a small framed card — its head, its two numbers (runs and redos,
// its price for a run), its name between two marks (the tool it runs on, its level), its state and what it does now. Hovering or
// focusing it shows its whole face beside it (the peek); a click shows only its work (solo). Free seats are narrow and dashed.
import { html, cls } from "../html.js";
import { Head, TIER_WORDS, ORKUI } from "../orkui.js";
import { agents, roles } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { solo } from "./arenastate.js";
import { BAND_WORDS, BAND_KEYWORD, columnOf, nowOf, statsOf, roleOf, memberView, raceOf } from "./arenawords.js";

const MARKS = `${ORKUI}/marks`;
/** One of orkUI's marks (a tool's, a level's) at 16 × 16 from the @2x image, pixelated; its word is its tooltip. */
function Mark({ name, tip }) {
  return html`<img class="ork-mark" src=${`${MARKS}/${name}.png`} srcset=${`${MARKS}/${name}@2x.png 2x`} alt="" title=${tip} draggable="false" />`;
}

const stateClass = (m) => (m.state === "needs" ? "is-alert" : m.state === "work" ? "is-ink" : "");

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

/** A member of the party row, or the leader (`lead`: its big head, its peek to the side). */
export function Member({ m, nodes, planning, lead = false }) {
  const role = roleOf(agents.value, m.slug), st = statsOf(m, role, lead);
  const col = lead ? [] : columnOf(m, nodes), line = nowOf(m, col, planning, lead);
  const view = memberView(m, st, line, raceOf(m.head));
  const on = solo.value === m.slug, dim = !!solo.value && !on;
  const pick = () => { solo.value = on ? "" : m.slug; };
  return html`<div class="arena-mcol" data-agent=${m.slug}>
    <button type="button" class=${cls("arena-member", { "is-on": on, "is-dim": dim, "is-lead": lead })} data-state=${m.state} data-agent=${m.slug}
      aria-pressed=${on} aria-label=${view.label} onClick=${pick}>
      <span class="arena-member__top"><span class=${cls("arena-port", stateClass(m))}>${m.head && html`<${Head} race=${m.head.race} tier=${m.head.tier} size=${lead ? "big" : "mid"} />`}${m.state === "work" && html`<span class="arena-port__spin shell-spin" aria-hidden="true">↻</span>`}</span>
      <span class="arena-nums"><span class="arena-num" title=${st.runsTip}>${st.runs}</span><span class="arena-num is-muted" title=${st.priceTip}>${st.price}</span></span></span>
      <span class="arena-member__name"><${Mark} name=${`harness-${st.harness.id}`} tip=${st.harnessTip} /><span class="arena-member__nm">${m.name}</span><${Mark} name=${`rank-${st.rank}`} tip=${st.rankTip} /></span>
      <span class=${cls("arena-member__state", view.tone)}>${view.words}${m.state === "work" ? " ↻" : ""}</span>
      <span class="arena-member__now">${line.now}</span>
    </button>
    <${Peek} m=${m} st=${st} line=${line} role=${role} view=${view} lead=${lead} side=${lead} nodes=${nodes} />
  </div>`;
}

/** A free seat: narrow, dashed; a click opens Edit the party. */
function Seat({ m, g }) {
  const band = m.band === "check" ? "checks" : "builds";
  return html`<div class="arena-mcol is-seat">
    <button type="button" class=${cls("arena-seat", { "is-dim": !!solo.value })} data-band=${m.band} title="A free seat: Edit the party to pick an agent"
      aria-label=${`A free seat, ${band}. Edit the party`} onClick=${() => openDialog("goal", { slug: g.slug })}>
      <span class="arena-seat__plus" aria-hidden="true">+</span><span class="arena-member__nm">A free seat</span><span class="arena-member__now">${band}</span></button>
  </div>`;
}

/** The party row (§5.1): the builders, the checkers, the free seats, each over its column. */
export function PartyRow({ g, members, nodes, planning, cols }) {
  return html`<section class="arena-team" aria-label="Party" style=${`--cols:${cols}`}>
    ${members.map((m) => (m.free ? html`<${Seat} key=${m.slug} m=${m} g=${g} />` : html`<${Member} key=${m.slug} m=${m} nodes=${nodes} planning=${planning} />`))}
  </section>`;
}
