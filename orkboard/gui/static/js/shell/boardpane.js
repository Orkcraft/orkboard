// The left column (docs/specs/33-v1-shell.md §6, spec 35 §11, spec 37 §8): two tabs, Board · Files. The Board: the goal select with
// New goal and the Target, Needs you (one list), then the ideas with New idea at their head. Files: the project's tree and its
// Git section. A click opens the preview.
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { town } from "../link.js";
import { board, track, OPS, useOps } from "../board/store.js";
import { Today } from "../board/today.js";
import { Goals, Ideas } from "../board/tracks.js";
import { Operations } from "../board/ops.js";
import { FilesPane } from "./files.js";
import { leftTab, refreshShell, openMap } from "./store.js";
import { projectsOn } from "./projects.js";

export function BoardPane() {
  const b = board.value, on = projectsOn.value ? leftTab.value : "board";
  useOps();
  // Needs you holds Operations' rows: the Board is read again when Operations moved.
  const rev = town.value?.ops_rev;
  useEffect(() => { if (rev) refreshShell(); }, [rev]);
  return html`<section class="shell-pane shell-board" aria-label=${on === "files" ? "Files" : "Board"}>
    ${projectsOn.value ? html`<header class="shell-pane__head shell-pane__tabs" role="tablist" aria-label="Board, Files">
      ${[["board", "Board"], ["files", "Files"]].map(([id, name]) => html`<button key=${id} role="tab" aria-selected=${on === id}
        class=${cls("shell-ltab", { "is-on": on === id })} onClick=${() => { leftTab.value = id; }}>${name}</button>`)}
    </header>` : html`<header class="shell-pane__head"><h2>Board</h2></header>`}
    <div class="shell-pane__body">
      ${on === "files" ? html`<${FilesPane} />`
        : b ? html`<button class="ork-btn shell-mapbtn" title="Your goals, ideas and tasks on one screen" onClick=${openMap}>Map</button><${Goals} />${track.value === OPS ? html`<${Operations} />` : html`<${Today} /><${Ideas} />`}` : html`<p class="ok-tone-muted">Opening the board…</p>`}
    </div>
  </section>`;
}
