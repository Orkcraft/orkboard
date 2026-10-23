// The party's deck (docs/specs/52-goal-types.md §3, decisions §65.3; it was the top bar's party switch, spec 50 §3.1): the left column's top line, 32 px over
// the leader's row — the party's short name, *k/n* (its done goals of all its goals, muted: a party has no end) and the work sign while it is at work —, at its
// right **Parties ⌄** (a small deck, the word, the chevron; no count of stops, spec 54 §2.4: its label alone says, for a screen reader, how many wait in the other
// parties). A press deals the parties as a spread (spread.js `Dealt`): a card per party in the Board's order, Operations when the
// project has them, then *+ New party*. The party picked is the party shown, kept per device. A new party saved gathers its seats' heads into the deck (spec 63 §3).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Head, Icon, ORKUI, Sign } from "../orkui.js";
import { town } from "../link.js";
import { board, track, OPS, goalList } from "../board/store.js";
import { keepGoal, keptGoal } from "../board/tracks.js";
import { mapData } from "../shell/store.js";
import { dialog, openDialog } from "../shell/modals.js";
import { currentProject } from "../shell/projects.js";
import { dropGather, gather, leaveParty } from "./arenastate.js";
import { APART_MS, LIT_MS, reducedMotion } from "./motion.js";
import { closeSpread, Dealt } from "./spread.js";
import { countOf, countTip, countWords, goalsOf, nodesOf, opStopsOf, plural, stopsOf } from "./arenawords.js";
import { tabWords } from "./goalwords.js";

/** The party shown: the picked one if the Map has it (or Operations, or the Board has it and the Map comes a moment later: a party just saved), else the
 *  one kept for this project, else the first. */
export function shownOf(goals, picked) {
  if (picked === OPS || goals.some((g) => g.slug === picked) || goalList().some((g) => g.slug === picked)) return picked;
  return (goals.find((g) => g.slug === keptGoal()) || goals[0])?.slug || "";
}

const opsOn = () => town.value?.ops_rev !== undefined;
const opStops = (needs) => opStopsOf(needs).length;
const hurt = (stops) => stops.some((s) => s.tone === "danger");               // one of them failed: the dot is the danger colour
const atWork = (g) => (g.party || []).some((x) => x.state === "work") || g.state === "reading";

/** The project's parties as the deck holds them: [{g, nodes, stops, failed, working}], and whether Operations is one more. */
function partiesOf() {
  const m = mapData.value, needs = board.value?.needs_you || [];
  const goals = goalsOf(m, goalList().map((g) => g.slug));
  return { goals: goals.map((g) => { const nodes = nodesOf(m, g.slug); const mine = stopsOf(needs, g, nodes); return { g, nodes, stops: mine.length, failed: hurt(mine), working: atWork(g) }; }),
    ops: opsOn(), opStops: opStops(needs), opFailed: hurt(opStopsOf(needs)) };
}

/** The stops that wait in the project's other parties and in Operations: those of every party but the one shown. */
export function othersStops(shown) {
  const { goals, ops, opStops: o } = partiesOf();
  return goals.filter((x) => x.g.slug !== shown).reduce((k, x) => k + x.stops, 0) + (ops && shown !== OPS ? o : 0);
}

/** How many edges the leader's row stands on (§3.3): one when the project has one other party or Operations, two when it has more. */
export function deckEdges(shown) {
  const { goals, ops } = partiesOf();
  return Math.min(2, goals.filter((x) => x.g.slug !== shown).length + (ops && shown !== OPS ? 1 : 0));
}

export const partiesLabel = (name, n) => `Parties: ${name} shown${n ? `, ${n === 1 ? "1 stop waits" : `${n} stops wait`} in the other parties` : ""}`;

/** A party's card in the spread: its leader's head, its name, *k/n done*, its members' small heads, a dot when stops wait in it (danger when one failed) and the work
 *  sign; the one shown raised. */
function PartyCard({ x, shown, press }) {
  const { g, nodes, working } = x, stops = shown ? 0 : x.stops, c = countOf(g, nodes);
  const team = (g.party || []).filter((p) => p.band !== "lead" && p.head);
  return html`<button type="button" class=${cls("arena-spread__card arena-deck__card", { "is-shown": shown })} data-goal=${g.slug}
      aria-label=${`${tabWords(g, nodes, stops, working)}${shown ? ", shown" : ""}`} title=${g.brief ? `${g.title} · ${g.brief}` : g.title} onClick=${press}>
    <span class="arena-deck__top">${g.leader?.head ? html`<${Head} race=${g.leader.head.race} tier=${g.leader.head.tier} size="mid" />` : html`<span></span>`}
      <span class="arena-deck__marks">${stops > 0 && html`<span class=${cls("arena-deck__dot", { "is-danger": x.failed })} aria-hidden="true"></span>`}${working && html`<${Sign} name="work" label="at work" />`}</span></span>
    <span class="arena-deck__name">${g.short || g.title}</span>
    <span class="arena-cap">${c.done}/${c.all} done</span>
    <span class="arena-deck__heads">${team.map((p) => html`<${Head} key=${p.slug} race=${p.head.race} tier=${p.head.tier} small=${true} />`)}</span>
    ${shown && html`<span class="arena-deck__shown">shown</span>`}
  </button>`;
}

/** The parties dealt from the deck (§3.4): a press picks one (the spread gathers, then the board shows it), opens Operations or New party. */
function PartiesSpread({ want, from, back, done }) {
  const { goals, ops, opStops: o, opFailed } = partiesOf();
  const project = currentProject.value?.name || "this project";
  const at = Math.max(0, want === OPS ? goals.length : goals.findIndex((x) => x.g.slug === want));
  const show = (gather, slug) => gather(() => {
    if (slug === track.value) return;
    closeSpread();
    leaveParty();
    track.value = slug;
  });
  return html`<${Dealt} name="Parties" cap=${html`<b>Parties of ${project}</b>`} from=${from} back=${back} done=${done} start=${at} cls="arena-deck__spread"
    cards=${(gather) => html`
      ${goals.map((x) => html`<${PartyCard} key=${x.g.slug} x=${x} shown=${x.g.slug === want} press=${() => show(gather, x.g.slug)} />`)}
      ${ops && html`<button type="button" class=${cls("arena-spread__card arena-deck__card", { "is-shown": want === OPS })} data-goal=${OPS}
          aria-label=${`Operations${want !== OPS && o ? `, ${plural(o, "stop waits", "stops wait")} for you` : ""}${want === OPS ? ", shown" : ""}`} title="Your everyday work by templates"
          onClick=${() => show(gather, OPS)}>
        <span class="arena-deck__top"><span class="arena-deck__icon"><${Icon} name="sliders" /></span><span class="arena-deck__marks">${want !== OPS && o > 0 && html`<span class=${cls("arena-deck__dot", { "is-danger": opFailed })} aria-hidden="true"></span>`}</span></span>
        <span class="arena-deck__name">Operations</span><span class="arena-cap">Your everyday work by templates</span>
        ${want === OPS && html`<span class="arena-deck__shown">shown</span>`}</button>`}
      <button type="button" class="arena-spread__card arena-deck__card is-blank" data-goal="" aria-label="New party" title="One of yours, or its leader, builders and checkers from the library"
        onClick=${() => gather(() => openDialog("goal"))}>
        <span class="arena-deck__plus"><${Icon} name="plus" /></span><span class="arena-deck__name">New party</span><span class="arena-cap">one of yours, or from the library</span></button>`} />`;
}

const GATHER_MS = 300, GATHER_SCALE = 0.4;     // a gathered head's travel (the deal's steps, arena.css `arena-gather`), and how large it is when it lands

/** A new party's heads gather into its deck (spec 63 §3.2): a copy of each head (`from`: [{race, tier, box}], the leader's first) travels over the page from its seat's box to the deck's centre at 0.4 of its
 *  size, 35 ms after the one before, and is gone on landing; when the last has landed the deck is lit once, as the quiet reward. The copies take no press and remove themselves. */
function gatherInto(deck, from) {
  const d = deck.getBoundingClientRect(), cx = d.left + d.width / 2, cy = d.top + d.height / 2;
  if (!from.length || !d.width || typeof deck.animate !== "function") return;
  let left = from.length, lit = false;
  const light = () => {
    if (lit) return;
    lit = true;
    copies.forEach((c) => c.remove());
    if (deck.isConnected) deck.animate([{ background: "var(--ork-ink)", color: "var(--ork-on-ink)" }, { background: "transparent" }], { duration: LIT_MS, easing: "steps(4, end)" });
  };
  const copies = from.map(({ race, tier, box }, i) => {
    const img = document.createElement("img");
    img.className = "ork-race__head arena-gather";
    img.src = `${ORKUI}/races/${race}-${tier}@2x.png`;
    img.alt = "";
    Object.assign(img.style, { left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px`, height: `${box.height}px` });
    img.style.setProperty("--dx", `${cx - (box.left + box.width / 2)}px`);
    img.style.setProperty("--dy", `${cy - (box.top + box.height / 2)}px`);
    img.style.setProperty("--s", String(GATHER_SCALE));
    img.style.setProperty("--delay", `${i * APART_MS}ms`);
    img.addEventListener("animationend", () => { img.remove(); if (--left === 0) light(); }, { once: true });
    document.body.append(img);
    return img;
  });
  setTimeout(light, GATHER_MS + APART_MS * from.length + 500);        // a page that never played them (a tab sent away) leaves nothing behind
}

/** The left column's top line over the leader (§3.2): the party shown (`g`; null for Operations), and Parties ⌄. It keeps the party shown for this device. */
export function PartyTop({ g = null, nodes = [] }) {
  const m = mapData.value;
  const goals = goalsOf(m, goalList().map((x) => x.slug));
  const want = m ? shownOf(goals, track.value) : track.value;
  // The party shown is `want`; `track` follows it only to start (a pick that no list has yet, a party just saved, shows the kept one until it does).
  useEffect(() => { if (m && !track.value && want) track.value = want; }, [m, want]);
  useEffect(() => { if (m && want && want !== OPS && want === track.value) keepGoal(want); }, [m, want, track.value]);
  const [dealt, setDealt] = useState(null);
  const btn = useRef();
  const waiting = gather.value, modal = dialog.value;
  useEffect(() => {                         // a new party was saved: its heads gather into the deck, in the first render that shows it once the dialog has closed (spec 63 §3.2)
    if (!waiting || waiting.party !== want || modal) return;
    dropGather(waiting);
    if (!reducedMotion() && !document.hidden && btn.current) gatherInto(btn.current, waiting.from);
  }, [want, waiting, modal]);
  const name = g ? g.short || g.title : want === OPS ? "Operations" : "No party yet", n = othersStops(want);
  const working = g && atWork(g);
  return html`<div class="arena-ptop">
    <span class="arena-ptop__name" title=${g?.title || name}>${name}</span>
    ${g && html`<span class="arena-ptop__count" title=${countTip(g, nodes)}>${countWords(g, nodes)}</span>`}
    ${working && html`<span class="arena-ptop__work"><${Sign} name="work" label="at work" /></span>`}
    <span class="arena-spacer"></span>
    <button type="button" ref=${btn} class="ork-btn quiet arena-ptop__deck" aria-haspopup="dialog" aria-expanded=${!!dealt} aria-label=${partiesLabel(name, n)}
      title="The project's parties" onClick=${(e) => setDealt(e.currentTarget.getBoundingClientRect())}>
      <span class="arena-ptop__cards" aria-hidden="true"><i></i><i></i><b></b></span>Parties<${Chev} dir="down" /></button>
    ${dealt && html`<${PartiesSpread} want=${want} from=${dealt} back=${btn.current} done=${() => setDealt(null)} />`}
  </div>`;
}
