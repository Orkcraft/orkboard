// The left column (docs/specs/49-one-window.md §4.4, docs/specs/50-parties-and-goals.md §3.3, docs/specs/52-goal-types.md §3.2, §4): its top line (the party
// shown and Parties ⌄: goaltabs.js), the party's leader with Process now standing on the deck (an edge behind it for each other party, two at most), then its
// Goals — *At work*, *Planning*, *New (n)* and *Flags (n) · k wait for main* — and at the foot the New goal pile. A goal's row: its pile (a back with the
// goal's element and an edge behind it for each of its open tasks, up to three), its title, its line, its mark and › (its screen, in the drawer). A press on
// the row picks the goal into the filter (a second press takes it out); hovering it peeks (the board shows only that goal's cards while the pointer is on
// the row). A goal of a type shows its sign before its title; a stop is marked once, by its sign (no alert edge, no alert words). A press on the pile deals the
// party's goal types (types.js); with none (an older host) it turns its top card over and opens New goal (≈ 0.42 s, in steps; at once under reduced motion).
import { useEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Elem, Icon, Sign } from "../orkui.js";
import { act, showIdea, showPlan } from "../shell/store.js";
import { dialog, openDialog } from "../shell/modals.js";
import { reducedMotion } from "./motion.js";
import { picks, peek, rawOpen, flagsOpen, flagsAll, togglePick, clearPicks } from "./arenastate.js";
import { litFlags } from "./flags.js";
import { powerOf } from "./arenawords.js";
import { typeSign } from "./stacks.js";
import { edgesOf, elementOf, flagRow, goalMark, goalsCount, listsOf, pickTip, waitsMain, workLine } from "./goalwords.js";
import { Member } from "./members.js";
import { PartyTop, deckEdges } from "./goaltabs.js";
import { TypesSpread } from "./types.js";

const TURN_MS = 420;
const SHOWN_FLAGS = 10;

const TONES = { danger: "is-danger", alert: "is-alert" };

/** One goal of the party. `plan`: a Planning row (its words come from the leader's reading); a raw goal (`raw`) opens on a press, it has no task to pick. */
function GoalRow({ g, n, plan = null, raw = false, party }) {
  const el = elementOf(n), mark = goalMark(n), on = (picks.value[party] || []).includes(n.slug), some = (picks.value[party] || []).length > 0;
  const stop = mark.sign === "alert";
  const words = raw || plan ? plan.words : workLine(n);
  const open = () => (plan?.kind === "plan" ? showPlan(n.slug, "", { via: "map" }) : showIdea(n.slug, { via: "map" }));
  const edges = raw || plan ? 0 : edgesOf(n);
  const enter = () => { peek.value = n.slug; }, leave = () => { if (peek.value === n.slug) peek.value = ""; };
  return html`<div class=${cls("arena-goal", { "is-on": on, "is-off": some && !on && !raw, "is-stop": stop })} data-slug=${n.slug} data-state=${stop ? "stop" : mark.sign === "work" ? "work" : "idle"}
      onMouseEnter=${raw ? undefined : enter} onMouseLeave=${raw ? undefined : leave}>
    <button type="button" class="arena-goal__main" aria-pressed=${raw ? undefined : on} title=${raw ? `${n.title} · ${words}` : `${n.title} · ${words}. ${pickTip(on)}`}
      onClick=${raw ? open : () => togglePick(party, n.slug)}>
      <span class="arena-goal__pile">${Array.from({ length: edges }, (_, i) => html`<i key=${i} class="arena-goal__edge" style=${`left:${(i + 1) * 2}px;top:${-(i + 1) * 2}px`}></i>`)}
        <span class="arena-goal__back"><${Elem} name=${el.name} dim=${el.dim} /></span></span>
      <span class="arena-goal__body"><span class="arena-goal__title">${typeSign(n, "arena-goal__type")}${n.short || n.title}</span>
        <span class="arena-goal__line">${words}</span></span>
      <span class=${cls("arena-goal__mark", TONES[mark.tone])} title=${mark.label || undefined}>${mark.sign && html`<${Sign} name=${mark.sign} />`}</span>
    </button>
    ${!raw && html`<button type="button" class="arena-goal__open" aria-label=${`Open ${n.title}`} title="Open it in the drawer" onClick=${open}><${Chev} dir="right" /></button>`}
  </div>`;
}

/** *Flags (n) · k wait for main*: the goals done that wait for main (a check), then the flags (the newest ten, then *All n*): the goal, its day, its price,
 *  how many of its tasks merged in their first round. A goal whose flag was raised a moment ago is lit once. */
function FlagsFold({ lists, g, nodes }) {
  const waits = waitsMain(g, nodes), n = lists.flagged.length, all = flagsAll.value, open = flagsOpen.value;
  if (!n && !waits) return null;
  const shown = all ? lists.flagged : lists.flagged.slice(0, SHOWN_FLAGS);
  return html`<div class="arena-flags">
    <button type="button" class="ork-btn quiet arena-fold" aria-expanded=${open} onClick=${() => { flagsOpen.value = !open; }}>Flags (${n})${waits ? ` · ${waits} wait for main` : ""}</button>
    ${open && html`<ul class="arena-flags__list">
      ${lists.waiting.map((x) => html`<li key=${x.slug}><button type="button" class="arena-flagrow" data-slug=${x.slug} onClick=${() => showIdea(x.slug, { via: "flags" })}>
        <${Sign} name="check" /> <span class="arena-flagrow__t">${x.short || x.title}</span><span class="arena-cap">in dev · waits for main</span></button></li>`)}
      ${shown.map((x) => html`<${FlagRow} key=${x.slug} n=${x} />`)}
      ${!all && n > SHOWN_FLAGS && html`<li><button type="button" class="ork-btn quiet" onClick=${() => { flagsAll.value = true; }}>All ${n}</button></li>`}
    </ul>`}
  </div>`;
}

function FlagRow({ n }) {
  const ref = useRef(), f = flagRow(n);
  useEffect(() => {                                   // a flag raised a moment ago is lit once, when it is on screen
    if (!litFlags.has(n.slug) || !ref.current) return;
    litFlags.delete(n.slug);
    if (!reducedMotion() && typeof ref.current.animate === "function") {
      ref.current.animate([{ background: "var(--ork-ink)", color: "var(--ork-on-ink)" }, { background: "transparent" }], { duration: 600, easing: "steps(4, end)" });
    }
  }, []);
  return html`<li><button ref=${ref} type="button" class="arena-flagrow" data-slug=${f.slug} data-flag=${f.at} title=${f.title} onClick=${() => showIdea(f.slug, { via: "flags" })}>
    <span class="arena-flagrow__flag"><${Sign} name="flag" /></span> <span class="arena-flagrow__t">${f.short}</span><span class="arena-cap">${f.words}</span></button></li>`;
}

/** The pile at the foot: a press deals the party's goal types (types.js); with none, it turns its top card over, then New goal opens; the card is put back when
 *  the dialog closes. */
function NewGoal({ g }) {
  const party = g.slug;
  const [drawing, setDrawing] = useState(false);
  const [dealt, setDealt] = useState(null);
  const timer = useRef(0), pile = useRef();
  const open = dialog.value;
  useEffect(() => { if (!open) setDrawing(false); }, [open]);
  useEffect(() => () => clearTimeout(timer.current), []);
  const press = (e) => {
    if (drawing || dealt) return;
    if ((g.types || []).length) { setDealt(e.currentTarget.getBoundingClientRect()); return; }
    setDrawing(true);
    if (reducedMotion()) openDialog("idea", { goal: party });
    else timer.current = setTimeout(() => openDialog("idea", { goal: party }), TURN_MS);
  };
  return html`<div class="arena-new">
    <button type="button" ref=${pile} class=${cls("arena-new__pile", { "is-drawing": drawing })} aria-label="New goal: your own, or pick its type" title="New goal: your own, or pick its type"
      aria-haspopup=${(g.types || []).length ? "dialog" : undefined} onClick=${press}>
      ${[3, 2, 1].map((i) => html`<i key=${i} class="arena-new__edge" style=${`left:${i * 2}px;top:${i * 2}px`}></i>`)}
      <span class="arena-new__card"><span class="arena-new__back"><${Icon} name="plus" /></span><span class="arena-new__face"></span></span>
    </button>
    <span class="arena-new__words"><b>New goal</b><span class="arena-cap">pick its type</span></span>
    ${dealt && html`<${TypesSpread} g=${g} from=${dealt} back=${pile.current} done=${() => setDealt(null)} />`}
  </div>`;
}

/** The leader with Process now, and under it the party's goals. */
export function Left({ g, nodes, planning, lead }) {
  const party = g.slug, lists = listsOf(g, nodes, lead?.name || "Taskmaster");
  const power = powerOf(planning.raw, lead?.name || "Taskmaster"), n = goalsCount(lists), picked = (picks.value[party] || []).length > 0;
  const edges = deckEdges(party);
  return html`<div class="arena-left">
    <${PartyTop} g=${g} nodes=${nodes} />
    <section class="arena-hero" aria-label="Leader" data-edges=${edges}>
      ${lead && html`<div class="arena-hero__deck">${Array.from({ length: edges }, (_, i) => html`<i key=${i} class="arena-hero__edge"
          style=${`inset:${-(i + 1) * 3}px ${-(i + 1) * 3}px ${(i + 1) * 3}px ${(i + 1) * 3}px`}></i>`).reverse()}<${Member} m=${lead} nodes=${nodes} planning=${planning} lead=${true} /></div>`}
      <button type="button" class="ork-btn arena-power" disabled=${power.off} title=${power.tip}
        onClick=${() => act("ideas.queue", { slug: power.slug, queue: "now", via: "party" })}>Process now · ${power.words}</button>
    </section>
    <section class="arena-goals" aria-label="Goals">
      <div class="arena-left__head"><h2 class="arena-lbl">Goals</h2><span class="ork-count">${n}</span><span class="arena-spacer"></span>
        ${picked && html`<button type="button" class="ork-btn quiet" title="Every goal of the party again" onClick=${() => clearPicks(party)}>Show all</button>`}</div>
      <div class="arena-deck">
        ${lists.work.length > 0 && html`<h3 class="arena-sec">At work</h3>`}
        ${lists.work.map((x) => html`<${GoalRow} key=${x.slug} g=${g} n=${x} party=${party} />`)}
        <h3 class="arena-sec">Planning</h3>
        ${!lists.planRows.length && !lists.raw.length && html`<p class="arena-cap">Nothing in Planning. A new goal starts here.</p>`}
        ${lists.planRows.map((r) => html`<${GoalRow} key=${r.slug} g=${g} n=${r.node} plan=${r} party=${party} />`)}
        ${lists.raw.length > 0 && html`<button type="button" class="ork-btn quiet arena-fold arena-raw" aria-expanded=${rawOpen.value} onClick=${() => { rawOpen.value = !rawOpen.value; }}>New (${lists.raw.length})</button>`}
        ${rawOpen.value && lists.raw.map((r) => html`<${GoalRow} key=${r.slug} g=${g} n=${r.node} plan=${r} raw=${true} party=${party} />`)}
        <${FlagsFold} lists=${lists} g=${g} nodes=${nodes} />
      </div>
      <${NewGoal} g=${g} />
    </section>
  </div>`;
}
