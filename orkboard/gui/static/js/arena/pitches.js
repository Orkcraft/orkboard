// Ideation's line (docs/specs/65-ideation.md §8, decisions §78): a party the Investor leads has pitches, not goals to build, so its field and its left
// column say them by state instead of the tasks' stacks. The left column: *Judging* (and the ones that failed), *Judged*, *New (n)*, *Sent (n)*, *Passed (n)*
// folded, each pitch a row that opens its screen (shell/pitchview.js). The field: under the party row (its four views, then the Skeptic), a line per pitch
// across the same columns — under each view its head, lit as that view answers (each lit once as it comes), under the Skeptic the decision's word
// (*Invest* · *Reshape* · *Pass*) — in *Judging*, *Judged*, *New* and *Sent*. The words are pitchwords.js's.
import { useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Elem, Head, Sign } from "../orkui.js";
import { showIdea } from "../shell/store.js";
import { useLit } from "./motion.js";
import { rawOpen, flagsOpen, sentOpen, solo } from "./arenastate.js";
import { stageOf } from "./arenawords.js";
import { elementOf } from "./goalwords.js";
import { answered, pitchLists, pitchMark, pitchWords, VIEWS } from "./pitchwords.js";

const TONES = { danger: "is-danger", alert: "is-alert" };
const open = (n) => showIdea(n.slug, { via: "map" });

/** A pitch's row in the left column: its element, its title, its line, its mark; a press opens its screen. */
function PitchRow({ n }) {
  const el = elementOf(n), mark = pitchMark(n), words = pitchWords(n);
  return html`<div class="arena-goal arena-pitchrow" data-slug=${n.slug} data-state=${n.pitch?.state || n.state}>
    <button type="button" class="arena-goal__main" title=${`${n.title} · ${words}`} aria-label=${`${n.title}: ${words}`} onClick=${() => open(n)}>
      <span class="arena-goal__pile"><span class="arena-goal__back"><${Elem} name=${el.name} dim=${el.dim} /></span></span>
      <span class="arena-goal__body"><span class="arena-goal__title">${n.short || n.title}</span><span class="arena-goal__line">${words}</span></span>
      <span class=${cls("arena-goal__mark", TONES[mark.tone])} title=${mark.label || undefined}>${mark.sign && html`<${Sign} name=${mark.sign} />`}</span>
      <span class="arena-goal__open" aria-hidden="true"><${Chev} dir="right" /></span>
    </button>
  </div>`;
}

/** A fold of the left column: *New (n)*, *Sent (n)*, *Passed (n)*. */
function Fold({ name, list, on, cls: kind }) {
  if (!list.length) return null;
  return html`<button type="button" class=${`ork-btn quiet arena-fold ${kind}`} aria-expanded=${on.value} onClick=${() => { on.value = !on.value; }}>${name} (${list.length})</button>
    ${on.value && list.map((n) => html`<${PitchRow} key=${n.slug} n=${n} />`)}`;
}

/** The left column's list for Ideation: the pitches being judged, the judged ones, then New, Sent and Passed folded. */
export function PitchGoals({ nodes }) {
  const l = pitchLists(nodes);
  return html`<div class="arena-deck">
    ${l.judging.length > 0 && html`<h3 class="arena-sec">Judging</h3>`}
    ${l.judging.map((n) => html`<${PitchRow} key=${n.slug} n=${n} />`)}
    <h3 class="arena-sec">Judged</h3>
    ${!l.judged.length && html`<p class="arena-cap">No pitch waits for you. A new pitch starts at New goal.</p>`}
    ${l.judged.map((n) => html`<${PitchRow} key=${n.slug} n=${n} />`)}
    <${Fold} name="New" list=${l.raw} on=${rawOpen} cls="arena-raw" />
    <${Fold} name="Sent" list=${l.sent} on=${sentOpen} cls="arena-sent" />
    <${Fold} name="Passed" list=${l.passed} on=${flagsOpen} cls="arena-passed" />
  </div>`;
}

/** Under a view: its head, lit once it has answered (and lit once more, the quiet reward, the moment it does). */
function ViewCell({ m, v, judging, dim }) {
  const ref = useRef(), on = !!v?.answered;
  useLit(ref, on);
  const said = `${m.name}: ${on ? "answered" : judging ? "not yet" : "no answer"}`;
  return html`<span ref=${ref} class=${cls("arena-pitch__view", { "is-on": on, "is-dim": dim })} data-view=${m.slug} data-on=${String(on)} title=${said}>
    ${m.head && html`<${Head} race=${m.head.race} tier=${m.head.tier} />`}${on ? html`<${Sign} name="check" />` : judging ? html`<span class="arena-pitch__dot" aria-hidden="true"></span>` : ""}</span>`;
}

/** Under the Skeptic: the decision's word once it is made; while judging, what is next (the case against, the decision). */
function DecisionCell({ n, dim }) {
  const p = n.pitch, d = p?.decision, st = p?.state || n.state;
  if (d && st !== "judging") {
    return html`<span class=${cls("arena-pitch__decision", { "is-dim": dim })} data-answer=${d.answer}><b class="arena-pitch__answer">${d.word}</b>
      ${d.reshaped && html`<span class="arena-cap">its kill reasons made it a reshape</span>`}</span>`;
  }
  if (st === "judging" && answered(p) >= VIEWS) {
    return html`<span class=${cls("arena-pitch__decision", { "is-dim": dim })}><${Sign} name="work" /> <span class="arena-cap">${p?.case ? "deciding" : "the case against"}</span></span>`;
  }
  return html`<span class=${cls("arena-pitch__decision", { "is-dim": dim })}></span>`;
}

/** A pitch across the party's columns: its title and line over a head under each view and the decision under the Skeptic; a press opens its screen. */
function PitchLine({ n, members, cols }) {
  const p = n.pitch, el = elementOf(n), judging = (p?.state || n.state) === "judging", by = solo.value;
  const words = judging ? `judging · ${answered(p)} of ${VIEWS} views` : pitchWords(n);        // what is next is said under the Skeptic
  return html`<button type="button" class=${cls("arena-pitch", { "is-run": judging })} data-slug=${n.slug} data-state=${p?.state || n.state}
      aria-label=${`${n.title}: ${words}`} title=${`${n.title} · ${words}`} onClick=${() => open(n)}>
    <span class="arena-pitch__top"><${Elem} name=${el.name} dim=${el.dim} /><span class="arena-pitch__title">${n.short || n.title}</span><span class="arena-cap">${words}</span></span>
    <span class="arena-pitch__line" style=${`--cols:${cols}`}>${members.map((m) => {
      const v = (p?.views || []).find((x) => x.slug === m.slug), dim = !!by && by !== m.slug;
      return v ? html`<${ViewCell} key=${m.slug} m=${m} v=${v} judging=${judging} dim=${dim} />`
        : m.band === "check" ? html`<${DecisionCell} key=${m.slug} n=${n} dim=${dim} />` : html`<span key=${m.slug}></span>`;
    })}</span>
  </button>`;
}

const SECTIONS = [["judging", "Judging"], ["judged", "Judged"], ["raw", "New"], ["sent", "Sent"]];

/** The field of Ideation: the stage words over the columns (*Views* over the first view, *Decision* over the Skeptic), then the pitches by state; the passed
 *  ones are folded in the left column. */
export function PitchField({ g, members, nodes, cols }) {
  const l = pitchLists(nodes), first = {};
  const heads = members.map((m) => {
    const st = !first[m.band] ? stageOf(g, m.band) : null;
    if (st) first[m.band] = true;
    return { key: m.slug, label: st?.word || "" };
  });
  const any = SECTIONS.some(([k]) => l[k].length);
  return html`<div class="arena-cols arena-pitches" style=${`--cols:${cols}`} role="group" aria-label="Pitches">
    <div class="arena-cols__head">${heads.map((h) => html`<span key=${h.key} class=${cls("arena-lbl", { "is-blank": !h.label })}>${h.label}</span>`)}</div>
    <div class="arena-pitches__list">
      ${!any && html`<p class="arena-cap arena-pitches__none">${l.passed.length ? `Nothing being judged or waiting: the passed ones are folded on the left, Passed (${l.passed.length}).`
        : "No pitch yet: New goal adds one; the four views and the Skeptic read it, then the Investor decides."}</p>`}
      ${SECTIONS.map(([k, name]) => l[k].length > 0 && html`<section key=${k} class="arena-pitches__sec" data-sec=${k} aria-label=${name}>
        <h3 class="arena-sec">${name}</h3>
        ${l[k].map((n) => html`<${PitchLine} key=${n.slug} n=${n} members=${members} cols=${cols} />`)}</section>`)}
    </div>
  </div>`;
}
