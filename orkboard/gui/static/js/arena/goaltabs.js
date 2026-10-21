// The party switch (docs/specs/50-parties-and-goals.md §3.1): in the top bar, right after the project switcher and Orkline, a segmented control — a segment per
// party of the Map in the Board's order: its leader's head (orkUI's small head), its short name, *k/n* (its done goals of all its goals, muted: a party has no end,
// so no meter and no %), the count of its stops in the warning count and a work sign while it is at work —, then Operations (when the project has them) and a last +
// (New party). The party picked is the party shown, kept per device. It is a `tablist` named *Parties*: arrows, Home and End move between the segments. A press
// on the segment of the party shown takes its filter away (§3.5).
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { Icon, Sign, WhoHead } from "../orkui.js";
import { town } from "../link.js";
import { board, track, OPS, goalList } from "../board/store.js";
import { keepGoal, keptGoal } from "../board/tracks.js";
import { mapData } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { clearPicks, leaveParty } from "./arenastate.js";
import { closeSpread } from "./spread.js";
import { countTip, countWords, goalsOf, nodesOf, opStopsOf, stopsOf } from "./arenawords.js";
import { tabWords } from "./goalwords.js";

/** The party shown: the picked one if the Map has it (or Operations, or the Board has it and the Map comes a moment later: a party just saved), else the
 *  one kept for this project, else the first. */
export function shownOf(goals, picked) {
  if (picked === OPS || goals.some((g) => g.slug === picked) || goalList().some((g) => g.slug === picked)) return picked;
  return (goals.find((g) => g.slug === keptGoal()) || goals[0])?.slug || "";
}

function Tab({ slug, on, pick, title, count, countTip: tip, stops, working, head, plain, label, hint }) {
  return html`<button type="button" role="tab" class=${cls("arena-gtab", { "is-on": on })} data-goal=${slug}
    aria-selected=${on} tabindex=${on ? 0 : -1} title=${hint} aria-label=${label} onClick=${() => pick(slug)}>
    ${plain ? html`<${Icon} name="sliders" />` : head && html`<span class="arena-gtab__head"><${WhoHead} head=${head} small=${true} /></span>`}<span class="arena-gtab__title">${title}</span>
    ${count && html`<span class="arena-gtab__count" title=${tip}>${count}</span>`}
    ${stops > 0 && html`<span class="ork-count warning arena-gtab__stops" aria-hidden="true">${stops}</span>`}
    ${working && html`<span class="arena-gtab__work"><${Sign} name="work" label="at work" /></span>`}</button>`;
}

export function PartySwitch() {
  const m = mapData.value, needs = board.value?.needs_you || [];
  const goals = goalsOf(m, goalList().map((g) => g.slug));
  const want = m ? shownOf(goals, track.value) : track.value;
  // The party shown is `want`; `track` follows it only to start (a pick that no list has yet, a party just saved, shows the kept one until it does).
  useEffect(() => { if (m && !track.value && want) track.value = want; }, [m, want]);
  useEffect(() => { if (m && want && want !== OPS && want === track.value) keepGoal(want); }, [m, want, track.value]);
  const ops = town.value?.ops_rev !== undefined;
  const pick = (slug) => {
    if (slug === track.value) { clearPicks(slug); return; }                 // the party shown: a press takes its filter away
    closeSpread();
    leaveParty();
    track.value = slug;
  };
  const move = (e) => {
    const all = [...e.currentTarget.querySelectorAll("[role=tab]")], at = all.indexOf(document.activeElement);
    const to = e.key === "ArrowRight" ? at + 1 : e.key === "ArrowLeft" ? at - 1 : e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : null;
    if (at < 0 || to === null) return;
    e.preventDefault();
    const next = all[(to + all.length) % all.length];
    next.focus();
    next.click();
  };
  return html`<div class="arena-pswitch">
    <div class="arena-pswitch__tabs" role="tablist" aria-label="Parties" onKeyDown=${move}>
      ${goals.map((g) => {
        const nodes = nodesOf(m, g.slug), stops = stopsOf(needs, g, nodes).length, working = (g.party || []).some((x) => x.state === "work") || g.state === "reading";
        return html`<${Tab} key=${g.slug} on=${want === g.slug} pick=${pick} slug=${g.slug} title=${g.short || g.title} head=${g.leader?.head} count=${countWords(g, nodes)}
          countTip=${countTip(g, nodes)} stops=${stops} working=${working} label=${tabWords(g, nodes, stops, working)}
          hint=${g.brief ? `${g.title} · ${g.brief}` : g.title} />`;
      })}
      ${ops && html`<${Tab} key=${OPS} on=${want === OPS} pick=${pick} slug=${OPS} title="Operations" stops=${opStopsOf(needs).filter((s) => s.kind !== "op_rules").length} plain=${true}
        label=${"Operations"} hint="Your everyday work by templates" />`}
    </div>
    <button type="button" class="arena-pswitch__new" aria-label="New party" title="New party: one of yours, or its leader, builders and checkers from the library" onClick=${() => openDialog("goal")}><${Icon} name="plus" /></button>
  </div>`;
}
