// New goal by its type on the desktop (docs/specs/52-goal-types.md §4.1, §4.3, decisions §65.4–§65.6): the party's goal types dealt from the New goal pile
// (`types` of ideas.map, the most used first) as a spread over *New goal for <party>*: *Your own goal* first (docs/specs/61-your-own-goal.md §1, the blank card:
// the pile's back with its +, the first card dealt), then a card each type: its sign, its name, its line and, when the party misses someone for it, *needs: <name>*
// with that agent's small head (muted ink: it is not a stop). A press turns the card over (the pile's turn, ≈ 0.42 s, in steps; at once under reduced motion)
// and New goal opens with it (shell/ideadialog.js). The join line's words, and a plan's missing line's
// (stops.js, board/idea.js), are said here. A type is told by its sign, never a colour.
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head, Icon, Sign } from "../orkui.js";
import { roles } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { reducedMotion } from "./motion.js";
import { Dealt } from "./spread.js";
import { pctOf } from "../spend.js";

const TURN_MS = 420;
const BANDS = { build: "builders", check: "checkers" };

/** The library's agent `id` (ideas.roles `library`): {name, race, tier, ...}, or null. */
export const agentOf = (id) => (roles.value?.library || []).find((a) => a.id === id) || null;

/** An agent's small head, from the library. */
export function AgentHead({ id }) {
  const a = agentOf(id);
  return a ? html`<${Head} race=${a.race} tier=${a.tier} small=${true} title=${a.name} />` : null;
}

/** *≈$0.40 a run*: the agent's tier's price (ideas.roles `tier_costs`), "" when there is none yet. */
export function runPrice(id) {
  const usd = Number(roles.value?.tier_costs?.[agentOf(id)?.tier]);
  return usd > 0 ? `≈${pctOf(usd) || `$${usd.toFixed(2)}`} a run` : "";
}

/** *needs: Artist* (and *, Copywriter* for a second). */
export const needsWords = (missing) => `needs: ${missing.map((m) => m.name).join(", ")}`;

/** A plan's missing line (§4.4): *No one in the party does pixel art: Artist would.*, *and 1 more* when it misses more than one kind. */
export function missingWords(missing) {
  const [m] = missing || [];
  if (!m) return "";
  const more = missing.length - 1;
  return `No one in the party does ${m.words}: ${m.name} would.${more ? ` and ${more} more` : ""}`;
}

/** The join line's words for one entry of a type's `missing`. */
export const joinWords = {
  free: (m) => `${m.name} joins the party`,
  swap: (m, out) => `Swap: ${out} leaves, ${m.name} joins`,
  without: (m) => `Without ${m.name}, its ${m.words} goes to the Grunt.`,
  full: (m) => `The party's ${BANDS[m.band] || "builders"} all have work open: ${m.name} can join from Edit the party when one is done. Till then its ${m.words} goes to the Grunt.`,
};

/** The shape of an entry's line: a free seat, a swap (someone can leave), or full (no one can). */
export const joinShape = (m) => (m.free ? "free" : (m.out || []).length ? "swap" : "full");

/** The join line (§4.3): one per entry of the type's `missing`, two at most. `state`: [{on, out}] by entry; `set(i, patch)`. */
export function JoinLine({ missing, state, set }) {
  return (missing || []).slice(0, 2).map((m, i) => {
    const shape = joinShape(m), s = state[i] || { on: false, out: "" };
    if (shape === "full") return html`<p key=${m.kind} class="ok-font-status ok-tone-muted arena-join is-full" data-agent=${m.agent}>${joinWords.full(m)}</p>`;
    const leaver = (m.out || []).find((o) => o.slug === s.out) || m.out?.[0];
    const price = runPrice(m.agent);
    return html`<div key=${m.kind} class="arena-join" data-agent=${m.agent} data-shape=${shape}>
      <label class="arena-join__line"><input type="checkbox" checked=${s.on} onChange=${(e) => set(i, { on: e.target.checked })} />
        <span>${shape === "free" ? joinWords.free(m) : joinWords.swap(m, leaver?.name || "")}</span><${AgentHead} id=${m.agent} />
        ${shape === "free" && price && html`<span class="ok-tone-muted" title="at API prices, not your bill">${price}</span>`}</label>
      ${shape === "swap" && html`<label class="arena-join__who"><span class="ok-font-label">Who leaves</span>
        <select class="ork-field" aria-label="Who leaves" value=${leaver?.slug || ""} disabled=${!s.on} onChange=${(e) => set(i, { out: e.target.value })}>
          ${m.out.map((o) => html`<option key=${o.slug} value=${o.slug}>${o.name} · ${o.runs === 1 ? "1 run" : `${o.runs} runs`} this week</option>`)}</select></label>`}
      ${!s.on && html`<p class="ok-font-status ok-tone-muted">${joinWords.without(m)}</p>`}
    </div>`;
  });
}

/** The join line's first state: the first entry that can join ticked (`ideas.add` takes one `join`), its leaver the first of `out`. */
export function joinStart(missing) {
  const list = (missing || []).slice(0, 2), first = list.findIndex((m) => joinShape(m) !== "full");
  return list.map((m, i) => ({ on: i === first, out: m.out?.[0]?.slug || "" }));
}

/** The join line's state after a tick: one entry ticked at most (`ideas.add` takes one `join`). */
export const joinSet = (state, i, patch) => state.map((s, k) => (k === i ? { ...s, ...patch } : patch.on ? { ...s, on: false } : s));

/** What `ideas.add` takes in `join`: the first ticked entry ({add, out?}), or null. */
export function joinValue(missing, state) {
  const i = (missing || []).slice(0, 2).findIndex((m, k) => state[k]?.on && joinShape(m) !== "full");
  if (i < 0) return null;
  const m = missing[i];
  return m.free ? { add: m.agent } : { add: m.agent, out: state[i].out || m.out[0].slug };
}

/** A type's card: its sign, its name, its line and what it needs; *Your own goal* (`t` null, the blank card): the pile's back with its +. */
function TypeCard({ t, turning, press }) {
  const needs = t?.missing || [];
  return html`<button type="button" class=${cls("arena-spread__card arena-type", { "is-blank": !t, "is-turning": turning })} data-type=${t?.id || ""}
      aria-label=${t ? `${t.name}: ${t.line}${needs.length ? `, ${needsWords(needs)}` : ""}` : "Your own goal: in your words"} onClick=${press}>
    <span class="arena-type__front">${t ? html`<${Sign} name=${t.sign} big=${true} /><span class="arena-type__name">${t.name}</span>
        <span class="arena-type__line">${t.line}</span>
        ${needs.length > 0 && html`<span class="arena-type__needs">${needs.map((m) => html`<${AgentHead} key=${m.agent} id=${m.agent} />`)}<span>${needsWords(needs)}</span></span>`}`
      : html`<span class="arena-type__back"><${Icon} name="plus" /></span><span class="arena-type__name">Your own goal</span>`}</span>
    <span class="arena-type__face"></span>
  </button>`;
}

/** *Your own goal*, then the party's types, dealt from the pile (spec 52 §4.1, spec 61 §1). `g`: the party; `from`: the pile's place; `back`: the pile (the focus goes back to it); `done`: gone. */
export function TypesSpread({ g, from, back, done }) {
  const [turning, setTurning] = useState("");
  const timer = useRef(0);
  useEffect(() => () => clearTimeout(timer.current), []);
  const types = g.types || [];
  const pick = (t) => {
    if (turning) return;
    const go = () => { done(); back?.focus(); openDialog("idea", { goal: g.slug, ...(t ? { type: t } : {}) }); };
    if (reducedMotion()) { go(); return; }
    setTurning(t?.id || "blank");
    timer.current = setTimeout(go, TURN_MS);
  };
  return html`<${Dealt} name=${`New goal for ${g.short || g.title}`} cap=${html`<b>New goal for ${g.short || g.title}</b>`} from=${from} back=${back} done=${done}
    cls="arena-types" cards=${() => html`
      <${TypeCard} t=${null} turning=${turning === "blank"} press=${() => pick(null)} />
      ${types.map((t) => html`<${TypeCard} key=${t.id} t=${t} turning=${turning === t.id} press=${() => pick(t)} />`)}`} />`;
}
