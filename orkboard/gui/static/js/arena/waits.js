// Waits for your look (docs/specs/49-one-window.md §5.5): the right column. A result per row, oldest first — its idea (one line), its
// title (a link to the result in the drawer), who made it, its tests or a check's findings, its size and price, and Merge into dev ·
// Send back · Drop (Review's own ResultActions). A result is not a signal (decisions §54.1): no alert colour. At the top, While you
// were away and Last week (Cards); at the foot, the Flags fold and Last week (MapFoot). One that was merged a moment ago folds out once.
import { html, cls } from "../html.js";
import { showResult, review, mapData } from "../shell/store.js";
import { ResultActions, Found, testsWords, foundWords, usd } from "../shell/review.js";
import { Cards } from "../board/cards.js";
import { MapFoot } from "../board/mapfoot.js";
import { useLeaving } from "../board/mapghost.js";
import { ideaOn, solo } from "./arenastate.js";
import { plural } from "./arenawords.js";

function Result({ r, nodes, leaving = false }) {
  const node = nodes.find((n) => n.slug === r.idea), task = node?.tasks.find((t) => t.id === r.task);
  const by = task?.by?.name || "";
  const t = r.check ? null : testsWords(r);
  const size = [r.diff ? plural(r.diff.files, "file", "files") : "", r.cost != null ? usd(r.cost) : ""].filter(Boolean).join(" · ");
  const dim = (!!ideaOn.value && ideaOn.value !== r.idea);
  return html`<div class=${cls("arena-result ork-frame", { "is-dim": dim, "map-leaving": leaving })} data-task=${r.task} data-idea=${r.idea} aria-hidden=${leaving ? "true" : undefined}>
    <span class="arena-cap arena-result__idea">${r.idea_title || node?.title || r.idea}</span>
    <button type="button" class="arena-link" title="Open the result: its code" onClick=${() => showResult(r.idea, r.task, { via: "map" })}>${r.title}${r.round > 1 ? html` <span class="shell-round">round ${r.round}</span>` : ""}</button>
    <span class="arena-cap">${by}${r.check ? " · its check" : ""}</span>
    ${t ? html`<span class=${cls("arena-result__tests", `is-${t.tone}`)}>${t.mark} ${t.text}${t.names.length ? html` <span class="ok-tone-muted">${t.names.join(", ")}</span>` : ""}</span>`
      : html`<span class="arena-result__tests">${foundWords(r.findings) || "Found nothing"}</span>`}
    <span class="arena-cap">${size}</span>
    ${leaving ? html`<span class="map-result__gone">merged into ${review.value?.into || "dev"}</span>`
      : html`<${Found} r=${r} />${r.conflict && html`<p class="ok-tone-error shell-conflict">⚠ ${r.conflict}</p>`}<${ResultActions} r=${r} />`}
  </div>`;
}

export function Looks({ g, results, nodes }) {
  const one = ideaOn.value ? results.filter((r) => r.idea === ideaOn.value) : results;
  const by = solo.value;
  const shown = by ? one.filter((r) => nodes.find((n) => n.slug === r.idea)?.tasks.find((t) => t.id === r.task)?.by.slug === by) : one;
  const who = by ? [...(nodes.flatMap((n) => n.tasks.map((t) => t.by)))].find((x) => x.slug === by)?.name : "";
  const gone = useLeaving(results, (r) => `${r.idea}/${r.task}`, (r) => nodes.find((n) => n.slug === r.idea)?.tasks.find((t) => t.id === r.task)?.state === "merged");
  const ghosts = gone.filter((r) => !shown.some((x) => x.idea === r.idea && x.task === r.task));
  return html`<aside class="arena-look" aria-label="Waits for your look">
    <div class="arena-look__head"><h2 class="arena-lbl">Waits for your look</h2>${shown.length > 0 && html`<span class="ork-count">${shown.length}</span>`}
      ${who && html`<span class="arena-cap">· only ${who}’s</span>`}</div>
    <div class="arena-look__list">
      <${Cards} />
      ${!shown.length && !ghosts.length && html`<p class="arena-cap">Nothing waits for your look. Results come here as their tasks finish.</p>`}
      ${shown.map((r) => html`<${Result} key=${r.idea + r.task} r=${r} nodes=${nodes} />`)}
      ${ghosts.map((r) => html`<${Result} key=${"gone" + r.idea + r.task} r=${r} nodes=${nodes} leaving=${true} />`)}
      ${mapData.value && html`<${MapFoot} m=${mapData.value} />`}
    </div>
  </aside>`;
}
