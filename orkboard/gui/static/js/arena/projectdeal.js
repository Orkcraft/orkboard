// The Orkmaster's two piles on the project's level (docs/specs/70-orkmaster-and-the-project.md §3, §4.1): **New party** under the field's head — a press deals the library's parties as cards in the host's order
// (`ideas.map` `project.deal`: Release first when flags wait and no party releases them, Ideation next when none judges pitches, the ones the project has last), each with its name, its heads, its line and its
// why; a press on a card opens New party with that party picked — and **New goal** at the field's foot — a press deals *Your own goal* and the goal types any party of the project is offered, and New goal
// opens without a party: the Orkmaster suggests one (projectparty.js). Both are dealt with `spread.js` `Dealt`, as a party's pile deals its goal types (types.js).
import { useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head, Icon } from "../orkui.js";
import { PROJECT } from "../board/store.js";
import { openDialog } from "../shell/modals.js";
import { agentOf, presetsOf, raceOfAgent } from "../shell/party.js";
import { Dealt } from "./spread.js";
import { TypesSpread } from "./types.js";
import { typesOf, whyWords } from "./projectwords.js";

/** The pile's markup: three edges and a card with the +, as a party's New goal pile. */
function Pile({ pile, label, onPress, haspopup }) {
  return html`<button type="button" ref=${pile} class="arena-new__pile" aria-label=${label} title=${label} aria-haspopup=${haspopup ? "dialog" : undefined} onClick=${onPress}>
    ${[3, 2, 1].map((i) => html`<i key=${i} class="arena-new__edge" style=${`left:${i * 2}px;top:${i * 2}px`}></i>`)}
    <span class="arena-new__card"><span class="arena-new__back"><${Icon} name="plus" /></span><span class="arena-new__face"></span></span>
  </button>`;
}

/** A library party's card in the Orkmaster's deal: its leader's head, its name, its members' small heads, its line, its why (*You have one* muted). */
function PartyCard({ p, entry, press }) {
  const lead = agentOf(p.lead), why = whyWords(entry), heads = [...p.build, ...p.check].map(agentOf).filter(Boolean);
  return html`<button type="button" class=${cls("arena-spread__card arena-type arena-type--party", { "is-have": entry?.why === "have" })} data-preset=${p.id} data-why=${entry?.why || ""}
      aria-label=${`${p.name}: ${p.line}${why ? `, ${why}` : ""}`} onClick=${press}>
    <span class="arena-type__front">
      <${Head} race=${lead ? raceOfAgent(lead) : p.race} tier=${lead?.tier || "elder"} />
      <span class="arena-type__name">${p.name}</span>
      <span class="arena-type__heads">${heads.map((a, i) => html`<${Head} key=${i} race=${raceOfAgent(a)} tier=${a.tier} small=${true} />`)}</span>
      <span class="arena-type__line">${p.line}</span>
      ${why && html`<span class="arena-type__why">${why}</span>`}
    </span>
    <span class="arena-type__face"></span>
  </button>`;
}

/** The parties dealt in the host's order; a press gathers them and opens New party with that one picked. */
function PartyDeal({ deal, from, back, done }) {
  const presets = presetsOf(), cards = deal.map((e) => [presets.find((p) => p.id === e.id), e]).filter(([p]) => p);
  const start = Math.max(0, cards.findIndex(([, e]) => e.why !== "have"));
  return html`<${Dealt} name="New party" cap=${html`<b>New party</b> · the Orkmaster deals the parties`} from=${from} back=${back} done=${done} start=${start} cls="arena-types arena-parties"
    cards=${(gather) => cards.map(([p, e]) => html`<${PartyCard} key=${p.id} p=${p} entry=${e} press=${() => gather(() => openDialog("goal", { preset: p.id }))} />`)} />`;
}

/** **New party**, under the field's head: the Orkmaster's deck. With an older host (no deal) a press opens New party as the column's last line does. */
export function NewPartyPile({ deal }) {
  const [from, setFrom] = useState(null), pile = useRef();
  const press = (e) => { if (!from) { if (deal.length) setFrom(e.currentTarget.getBoundingClientRect()); else openDialog("goal"); } };
  return html`<div class="arena-new arena-pjnew">
    <${Pile} pile=${pile} label="New party: the Orkmaster deals the parties" onPress=${press} haspopup=${deal.length > 0} />
    <span class="arena-new__words"><b>New party</b><span class="arena-cap">the Orkmaster deals them</span></span>
    ${from && html`<${PartyDeal} deal=${deal} from=${from} back=${pile.current} done=${() => setFrom(null)} />`}
  </div>`;
}

/** **New goal**, at the field's foot: the goal types of the project's parties dealt (*Your own goal* first), then New goal without a party; the Orkmaster suggests it. */
export function NewGoalPile({ goals }) {
  const [from, setFrom] = useState(null), pile = useRef();
  const types = typesOf(goals), at = { slug: PROJECT, title: "the project", short: "the project", types };
  const press = (e) => { if (!from) { if (types.length) setFrom(e.currentTarget.getBoundingClientRect()); else openDialog("idea", { goal: PROJECT }); } };
  return html`<div class="arena-new arena-pjgoal">
    <${Pile} pile=${pile} label="New goal: your own, or pick its type" onPress=${press} haspopup=${types.length > 0} />
    <span class="arena-new__words"><b>New goal</b><span class="arena-cap">its party is suggested</span></span>
    ${from && html`<${TypesSpread} g=${at} from=${from} back=${pile.current} done=${() => setFrom(null)} />`}
  </div>`;
}

