// The parties in the left column (docs/specs/69-parties-in-the-column.md, decisions §84; it was the party's deck, spec 52 §3, and the parties' spread): from the top the
// project switcher (shell/projects.js, as wide as the column), then a heading for each party in the Board's order — its leader's head, its whole name (two lines, then cut,
// the title whole), *k/n*, the work sign while it is at work and, on a closed party, one sign for the stops that wait in it where they cannot be seen (! , ✗ when one failed:
// §65.2) —, Operations when the project has them, then *+ New party*. One party is open, the one the board shows, with its body under its heading (`body`: goals.js `Left`);
// a press on a closed heading shows that party (the party switch: the board redraws in place, the party kept per device), a press on the open one does nothing. ↑ and ↓ move between
// the headings. A new party saved gathers its seats' heads onto its heading's head (spec 63 §3, goaltabs.js `gatherInto`). The column scrolls under the project's line.
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Head, Icon, Sign } from "../orkui.js";
import { track, OPS } from "../board/store.js";
import { keepGoal } from "../board/tracks.js";
import { mapData } from "../shell/store.js";
import { dialog, openDialog } from "../shell/modals.js";
import { ProjectSwitcher } from "../shell/projects.js";
import { dropGather, gather, leaveParty } from "./arenastate.js";
import { reducedMotion } from "./motion.js";
import { countTip, countWords, plural } from "./arenawords.js";
import { gatherInto, partiesOf, shownOf } from "./goaltabs.js";

let scrolled = 0;                                       // the column's scroll, kept across the redraw a switch makes (the party is keyed, the list is drawn again)

/** Shows another party (or Operations): what was hovered or opened on the last one goes, the picks stay with their party. */
function show(slug, want) {
  if (slug === want) return;
  leaveParty();
  track.value = slug;
}

/** What waits in a closed party, as one sign: ✗ in the danger colour when one failed, else !; its title says how many. */
function WaitSign({ n, failed, name }) {
  if (!n) return null;
  return html`<span class=${cls("arena-phead__stop", failed ? "is-danger" : "is-alert")} title=${`${plural(n, "waits", "wait")} in ${name}`}><${Sign} name=${failed ? "cross" : "alert"} /></span>`;
}

/** A party's heading: one button, its leader's head, its name, the work sign, *k/n*, the stop sign (closed only). */
function Heading({ x, open, want }) {
  const { g, nodes, working } = x, name = g.short || g.title, stops = open ? 0 : x.stops;
  return html`<button type="button" class=${cls("arena-phead", { "is-open": open })} data-goal=${g.slug} data-state=${open ? "open" : "closed"} aria-expanded=${open} aria-current=${open ? "true" : undefined}
      title=${open ? `${name} is open` : `Open ${name}`} onClick=${() => show(g.slug, want)}>
    <span class="arena-plist__head">${g.leader?.head ? html`<${Head} race=${g.leader.head.race} tier=${g.leader.head.tier} />` : null}</span>
    <span class="arena-phead__name" title=${g.title}>${name}</span>
    ${working && html`<span class="arena-phead__work"><${Sign} name="work" label="at work" /></span>`}
    <span class="arena-phead__count" title=${countTip(g, nodes)}>${countWords(g, nodes)}</span>
    <${WaitSign} n=${stops} failed=${x.failed} name=${name} />
  </button>`;
}

function OpsHeading({ ps, open, want }) {
  const n = open ? 0 : ps.opStops;
  return html`<button type="button" class=${cls("arena-phead", { "is-open": open })} data-goal=${OPS} data-state=${open ? "open" : "closed"} aria-expanded=${open} aria-current=${open ? "true" : undefined}
      title=${open ? "Operations is open" : "Open Operations"} onClick=${() => show(OPS, want)}>
    <span class="arena-plist__head arena-plist__icon"><${Icon} name="sliders" /></span>
    <span class="arena-phead__name">Operations</span>
    <${WaitSign} n=${n} failed=${ps.opFailed} name="Operations" />
  </button>`;
}

/** The left column: the project's line, the parties, Operations, *+ New party*; `body` is the open party's, drawn under its heading. */
export function PartyList({ body = null }) {
  const m = mapData.value, root = useRef(), list = useRef();
  const ps = partiesOf(), goals = ps.goals.map((x) => x.g);
  const want = m ? shownOf(goals, track.value) : track.value;
  // The party shown is `want`; `track` follows it only to start (a pick that no list has yet, a party just saved, shows the kept one until it does).
  useEffect(() => { if (m && !track.value && want) track.value = want; }, [m, want]);
  useEffect(() => { if (m && want && want !== OPS && want === track.value) keepGoal(want); }, [m, want, track.value]);
  const waiting = gather.value, modal = dialog.value;
  useEffect(() => {                         // a new party was saved: its heads gather onto its heading's head, in the first render that shows it once the dialog has closed (spec 63 §3.2)
    if (!waiting || waiting.party !== want || modal) return;
    dropGather(waiting);
    const head = root.current?.querySelector(`.arena-phead[data-goal="${CSS.escape(want)}"] .arena-plist__head`);
    if (!reducedMotion() && !document.hidden && head) gatherInto(head, waiting.from);
  }, [want, waiting, modal]);
  useLayoutEffect(() => { if (list.current) list.current.scrollTop = scrolled; }, []);
  const move = (e) => {                     // ↑ and ↓ move between the headings
    const k = e.key === "ArrowDown" ? 1 : e.key === "ArrowUp" ? -1 : 0;
    if (!k || !e.target.matches?.(".arena-phead, .arena-pnew")) return;
    const all = [...root.current.querySelectorAll(".arena-phead, .arena-pnew")], at = all.indexOf(e.target);
    e.preventDefault();
    all[Math.min(all.length - 1, Math.max(0, at + k))]?.focus();
  };
  const open = (slug) => slug === want;
  return html`<aside class="arena-left" aria-label="Parties" ref=${root} onKeyDown=${move}>
    <div class="arena-left__proj"><${ProjectSwitcher} /></div>
    <div class="arena-plist" ref=${list} onScroll=${(e) => { scrolled = e.currentTarget.scrollTop; }}>
      ${ps.goals.map((x) => html`<section key=${x.g.slug} class=${cls("arena-party", { "is-open": open(x.g.slug) })}>
        <${Heading} x=${x} open=${open(x.g.slug)} want=${want} />
        ${open(x.g.slug) && body}
      </section>`)}
      ${ps.ops && html`<section class=${cls("arena-party", { "is-open": want === OPS })}><${OpsHeading} ps=${ps} open=${want === OPS} want=${want} /></section>`}
      <button type="button" class="arena-pnew" title="One of yours, or its leader, builders and checkers from the library" onClick=${() => openDialog("goal")}>
        <span class="arena-plist__head arena-plist__icon"><${Icon} name="plus" /></span><span class="arena-phead__name">+ New party</span></button>
    </div>
  </aside>`;
}
