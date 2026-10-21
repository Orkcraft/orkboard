// Waits for your look (docs/specs/49-one-window.md §5.5, docs/specs/50-parties-and-goals.md §3.5): the right column. A result per row, oldest first —
// its goal's element and name (one line), its title (a link to the result in the drawer), who made it, its tests or a check's findings, its size and price,
// and Merge into dev · Send back · Drop (Review's own ResultActions). A result is not a signal (decisions §54.1): no alert colour. The goals the filter takes
// away leave with the rest. At the top, While you were away and Last week (Cards); at the foot, Last week (MapFoot). One that was merged a moment ago folds out once.
import { useRef } from "preact/hooks";
import { html, cls } from "../html.js";
import { Elem, Sign } from "../orkui.js";
import { showResult, review } from "../shell/store.js";
import { ResultActions, Found, testsWords, usd } from "../shell/review.js";
import { Cards } from "../board/cards.js";
import { MapFoot } from "../board/mapfoot.js";
import { useColumn } from "./motion.js";
import { solo } from "./arenastate.js";
import { plural } from "./arenawords.js";
import { elementOf, inFilter, leaveOf } from "./goalwords.js";

function Result({ r, nodes, sign = "", quiet = false, fresh = false }) {
  const leaving = !!sign || quiet;
  const node = nodes.find((n) => n.slug === r.idea), task = node?.tasks.find((t) => t.id === r.task);
  const by = task?.by?.name || "", el = elementOf(node);
  const t = testsWords(r);
  const size = [r.diff ? plural(r.diff.files, "file", "files") : "", r.cost != null ? usd(r.cost) : ""].filter(Boolean).join(" · ");
  return html`<div class=${cls("arena-result ork-frame", { "is-leaving": !!sign, "is-gone": quiet, "is-drawn": fresh })} data-key=${`${r.idea}/${r.task}`} data-task=${r.task} data-idea=${r.idea}
      data-sign=${sign || undefined} aria-hidden=${leaving ? "true" : undefined}>
    <span class="arena-cap arena-result__idea"><${Elem} name=${el.name} dim=${el.dim} />${r.idea_title || node?.title || r.idea}</span>
    <button type="button" class="arena-link" title="Open the result: its code" onClick=${() => showResult(r.idea, r.task, { via: "map" })}>${r.title}${r.round > 1 ? html` <span class="shell-round">round ${r.round}</span>` : ""}</button>
    <span class="arena-cap">${by}${r.check ? " · its check" : ""}</span>
    <span class=${cls("arena-result__tests", `is-${t.tone}`)}>${t.mark && html`<${Sign} name=${t.mark} /> `}${t.text}${t.names.length ? html` <span class="ok-tone-muted">${t.names.join(", ")}</span>` : ""}</span>
    <span class="arena-cap">${size}</span>
    ${html`<${Found} r=${r} />${r.conflict && html`<p class="ok-tone-error shell-conflict">⚠ ${r.conflict}</p>`}`}
    ${leaving ? html`<span class="arena-cap">${sign === "check" ? `merged into ${review.value?.into || "dev"}` : sign === "cross" ? "dropped" : ""}</span>` : html`<${ResultActions} r=${r} />`}
    ${!!sign && html`<span class="arena-task__flash">${sign !== "fade" && html`<${Sign} name=${sign} big=${true} />`}</span>`}
  </div>`;
}

export function Looks({ g, results, nodes, shown }) {
  const one = shown.length ? results.filter((r) => inFilter(shown, r.idea)) : results;
  const by = solo.value;
  const there = by ? one.filter((r) => nodes.find((n) => n.slug === r.idea)?.tasks.find((t) => t.id === r.task)?.by.slug === by) : one;
  const who = by ? [...(nodes.flatMap((n) => n.tasks.map((t) => t.by)))].find((x) => x.slug === by)?.name : "";
  const ref = useRef(), at = useRef({ nodes, shown });
  at.current = { nodes, shown };
  const list = useColumn(ref, there, (r) => `${r.idea}/${r.task}`, (r) => leaveOf(at.current.nodes, at.current.shown, r.idea, r.task));
  return html`<aside class="arena-look" aria-label="Waits for your look">
    <div class="arena-look__head"><h2 class="arena-lbl">Waits for your look</h2>${there.length > 0 && html`<span class="ork-count">${there.length}</span>`}
      ${who && html`<span class="arena-cap">· only ${who}’s</span>`}</div>
    <div class="arena-look__list" ref=${ref}>
      <${Cards} />
      ${!list.length && html`<p class="arena-cap">${shown.length && results.length ? "Nothing of these goals" : "Nothing waits for your look. Results come here as their tasks finish."}</p>`}
      ${list.map((e) => html`<${Result} key=${e.key} r=${e.it} nodes=${nodes} sign=${e.sign} quiet=${e.quiet} fresh=${e.fresh} />`)}
      <${MapFoot} />
    </div>
  </aside>`;
}
