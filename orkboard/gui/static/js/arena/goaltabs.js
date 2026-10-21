// The goal tabs (docs/specs/49-one-window.md §4.1): a tab per goal of the Map in the Board's order — the flag, its short title, a meter of
// five cells and its %, the count of its stops in the warning count, ↻ while its party is at work — then Operations (when the project
// has them), + New goal and, at the row's end, Merge into dev ▾. The goal picked is the goal shown, kept per device. Arrows, Home and
// End move between the tabs.
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { Chev, Icon } from "../orkui.js";
import { town } from "../link.js";
import { board, track, OPS, goalList } from "../board/store.js";
import { keepGoal, keptGoal } from "../board/tracks.js";
import { progressOf } from "../board/maplayout.js";
import { mapData, review } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { clearPicks } from "./arenastate.js";
import { goalsOf, nodesOf, opStopsOf, stopsOf } from "./arenawords.js";

/** The goal shown: the picked one if the Map has it (or Operations), else the one kept for this project, else the first. */
export function shownOf(goals, picked) {
  if (picked === OPS || goals.some((g) => g.slug === picked)) return picked;
  return (goals.find((g) => g.slug === keptGoal()) || goals[0])?.slug || "";
}

function Tab({ slug, on, pick, title, pct, stops, working, tip, meter, plain }) {
  return html`<button type="button" role="tab" class=${cls("arena-gtab", { "is-on": on })} data-goal=${slug}
    aria-selected=${on} tabindex=${on ? 0 : -1} title=${tip}
    aria-label=${[title, pct != null ? `${pct} %` : "", stops ? (stops === 1 ? "1 stop waits for you" : `${stops} stops wait for you`) : "", working ? "at work" : ""].filter(Boolean).join(", ")}
    onClick=${() => pick(slug)}>
    <${Icon} name=${plain ? "sliders" : "flag"} /><span class="arena-gtab__title">${title}</span>
    ${meter && html`<span class="ork-meter" aria-hidden="true">${[0, 1, 2, 3, 4].map((i) => html`<i key=${i} class=${i < Math.round(pct / 20) ? "on" : ""}></i>`)}</span><b>${pct} %</b>`}
    ${stops > 0 && html`<span class="ork-count warning arena-gtab__stops" aria-hidden="true">${stops}</span>`}
    ${working && html`<span class="arena-muted" aria-hidden="true">↻</span>`}</button>`;
}

export function GoalTabs() {
  const m = mapData.value, needs = board.value?.needs_you || [];
  const goals = goalsOf(m, goalList().map((g) => g.slug));
  const want = m ? shownOf(goals, track.value) : track.value;
  useEffect(() => { if (m && want !== track.value) track.value = want; }, [m, want]);
  useEffect(() => { if (m && want && want !== OPS) keepGoal(want); }, [m, want]);
  const ops = town.value?.ops_rev !== undefined;
  const into = review.value?.into;
  const pick = (slug) => { if (slug !== track.value) { clearPicks(); track.value = slug; } };
  const move = (e) => {
    const all = [...e.currentTarget.querySelectorAll("[role=tab]")], at = all.indexOf(document.activeElement);
    const to = e.key === "ArrowRight" ? at + 1 : e.key === "ArrowLeft" ? at - 1 : e.key === "Home" ? 0 : e.key === "End" ? all.length - 1 : null;
    if (at < 0 || to === null) return;
    e.preventDefault();
    const next = all[(to + all.length) % all.length];
    next.focus();
    next.click();
  };
  return html`<div class="arena-tabs">
    <div class="arena-tabs__list" role="tablist" aria-label="Goals" onKeyDown=${move}>
      ${goals.map((g) => {
        const nodes = nodesOf(m, g.slug), pct = progressOf(nodes), stops = stopsOf(needs, g, nodes).length;
        const when = (g.done_when || []).join(", ");
        return html`<${Tab} key=${g.slug} on=${want === g.slug} pick=${pick} slug=${g.slug} title=${g.short || g.title} pct=${pct} stops=${stops} meter=${true}
          working=${(g.party || []).some((x) => x.state === "work") || g.state === "reading"}
          tip=${`${g.title} · ${pct} % of the way${when ? ` · done when ${when}` : ""}`} />`;
      })}
      ${ops && html`<${Tab} key=${OPS} on=${want === OPS} pick=${pick} slug=${OPS} title="Operations" stops=${opStopsOf(needs).length} plain=${true} tip="Your everyday work by templates" />`}
    </div>
    <button type="button" class="ork-btn quiet arena-tabs__new" onClick=${() => openDialog("goal")}>+ New goal</button>
    <span class="arena-spacer"></span>
    ${into && html`<button type="button" class="ork-btn arena-tabs__into" aria-haspopup="dialog" onClick=${() => openDialog("into")}>Merge into <b>${into}</b><${Chev} /></button>`}
  </div>`;
}
