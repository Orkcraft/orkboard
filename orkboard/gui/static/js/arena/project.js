// The project's level (docs/specs/70-orkmaster-and-the-project.md §2–§3, decisions §85): a press on the Orkmaster in the project's line shows the whole of the project in place of one party —
// a column for each party in the Board's order (Operations is not one), its head (the leader's head, its name, *k/n*; a press opens that party), under it its goals as decks (132 × 72 at most:
// the goal's element, its type's sign, its title, its state's words) grouped *Planning*, *At work*, *Waits for main*, then *Flags (n)* folded. A press on a deck opens the goal's screen in the drawer.
// Wider than the field the columns scroll sideways and the heads stay. Hovering or focusing a deck draws, with arrows.js, a link to each deck its route names in another column (the pitch it came from,
// the release it went into); nothing at rest. Above the columns the Orkmaster's head and *New party* (its deck: projectdeal.js), below them *New goal* (projectdeal.js, a goal's party from the Orkmaster).
// The code's goal is a party; its idea is a goal; its deck is a goal drawn small, never a word a person reads.
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Elem, Head, Sign } from "../orkui.js";
import { PROJECT, goalList } from "../board/store.js";
import { showIdea, showPlan } from "../shell/store.js";
import { countTip, countWords, goalsOf, nodesOf } from "./arenawords.js";
import { elementOf, goalMark } from "./goalwords.js";
import { pitchMark } from "./pitchwords.js";
import { typeSign } from "./stacks.js";
import { ArrowLines, segment } from "./arrows.js";
import { PartyList, show } from "./partylist.js";
import { NewGoalPile, NewPartyPile } from "./projectdeal.js";
import { GROUPS, PARTIES_WORDS, THE_PROJECT, deckCount, decksOf, emptyWords, linksOf } from "./projectwords.js";

const TONES = { danger: "is-danger", alert: "is-alert" };

/** One goal as a deck: its element and type sign, its title (two lines) and its state's words. A press opens its screen (its plan when the plan waits). */
function Deck({ d, party, lit, setLit }) {
  const n = d.n, el = elementOf(n), mark = n.pitch ? pitchMark(n) : goalMark(n);
  const open = () => (n.needs_you === "plan" ? showPlan(n.slug, "", { via: "map" }) : showIdea(n.slug, { via: "map" }));
  const on = () => setLit(n.slug), off = () => setLit((now) => (now === n.slug ? "" : now));
  return html`<button type="button" class=${cls("arena-deck", { "is-lit": lit === n.slug })} data-slug=${n.slug} data-party=${party} title=${`${n.title} · ${d.words}`}
      aria-label=${`${n.title}, ${d.words}`} onClick=${open} onMouseEnter=${on} onMouseLeave=${off} onFocus=${on} onBlur=${off}>
    <span class="arena-deck__top"><${Elem} name=${el.name} dim=${el.dim} />${typeSign(n, "arena-goal__type")}<span class="arena-spacer"></span>
      ${mark.sign && html`<span class=${cls("arena-deck__mark", TONES[mark.tone])} title=${mark.label || undefined}><${Sign} name=${mark.sign} /></span>`}</span>
    <span class="arena-deck__title">${n.short || n.title}</span>
    <span class="arena-deck__line">${d.words}</span>
  </button>`;
}

/** A party's column: its head, its groups of decks, its Flags folded. */
function Column({ g, nodes, lit, setLit }) {
  const [flags, setFlags] = useState(false), d = decksOf(g, nodes), name = g.short || g.title;
  const decks = (list) => list.map((x) => html`<${Deck} key=${x.n.slug} d=${x} party=${g.slug} lit=${lit} setLit=${setLit} />`);
  return html`<section class="arena-pcol" data-goal=${g.slug} aria-label=${name}>
    <button type="button" class="arena-pcol__head" title=${`Open ${name}`} onClick=${() => show(g.slug, PROJECT)}>
      <span class="arena-plist__head">${g.leader?.head ? html`<${Head} race=${g.leader.head.race} tier=${g.leader.head.tier} />` : null}</span>
      <span class="arena-pcol__name" title=${g.title}>${name}</span>
      <span class="arena-phead__count" title=${countTip(g, nodes)}>${countWords(g, nodes)}</span>
    </button>
    ${deckCount(d) === 0 && html`<p class="arena-cap arena-pcol__empty">${emptyWords(name)}</p>`}
    ${GROUPS.map(([key, label]) => d[key].length > 0 && html`<div key=${key} class="arena-pgroup" data-group=${key}><h3 class="arena-sec">${label}</h3>${decks(d[key])}</div>`)}
    ${d.flags.length > 0 && html`<div class="arena-pgroup" data-group="flags">
      <button type="button" class="ork-btn quiet arena-fold" aria-expanded=${flags} onClick=${() => setFlags(!flags)}><${Chev} dir=${flags ? "down" : "right"} /> Flags (${d.flags.length})</button>
      ${flags && decks(d.flags)}</div>`}
  </section>`;
}

/** The links the lit deck's route draws, in the host's coordinates: the two decks' boxes joined by an arrow, from the earlier step to the later. */
function useLinks(host, nodes, lit) {
  const [lines, setLines] = useState([]);
  useLayoutEffect(() => {
    const el = host.current, mine = lit ? linksOf(nodes).filter((l) => l.from === lit || l.to === lit) : [];
    if (!el || !mine.length) { setLines((was) => (was.length ? [] : was)); return; }
    const base = el.getBoundingClientRect(), box = (slug) => {
      const x = el.querySelector(`.arena-deck[data-slug="${CSS.escape(slug)}"]`);
      if (!x) return null;
      const r = x.getBoundingClientRect();
      return { x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
    };
    setLines(mine.map((l) => [l, box(l.from), box(l.to)]).filter(([, a, b]) => a && b).map(([l, a, b]) => segment(l.key, a, b)));
  }, [lit, nodes]);
  return lines;
}

/** The project's level: the field in place of a party's. `stops`: the one hand's, as Operations' field has it. */
export function Project({ m, stops }) {
  const parties = goalsOf(m, goalList().map((x) => x.slug)), [lit, setLit] = useState(""), host = useRef();
  const lines = useLinks(host, m.nodes || [], lit);
  const ork = m.project?.orkmaster;
  return html`<div class="arena arena-project" data-goal=${PROJECT}>
    <${PartyList} />
    <div class="arena-ops__main arena-project__main">
      <div class="arena-pjtop">${ork && html`<${Head} race=${ork.race || "peon"} tier=${ork.tier || "elder"} />`}<h2 class="arena-pjtop__title">${THE_PROJECT}</h2>
        <span class="arena-cap">${PARTIES_WORDS}</span></div>
      <${NewPartyPile} deal=${m.project?.deal || []} />
      <section class="arena-project__body" aria-label=${THE_PROJECT}>
        <div class="arena-project__cols" ref=${host}>
          ${parties.map((g) => html`<${Column} key=${g.slug} g=${g} nodes=${nodesOf(m, g.slug)} lit=${lit} setLit=${setLit} />`)}
          <${ArrowLines} lines=${lines} />
        </div>
      </section>
      <${NewGoalPile} goals=${parties} />
      ${stops}
    </div>
  </div>`;
}
