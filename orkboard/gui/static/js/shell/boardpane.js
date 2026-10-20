// The left column (docs/specs/33-v1-shell.md §6, spec 35 §11, spec 37 §8), its screens split as the phone's: Board · Needs you ·
// Files. The Board: the goal shown (the select, with New goal and the Target; its card: its party's heads, its line, how far its
// ideas are), then that goal's ideas with New idea at their head. Needs you: every goal's rows, its count on its tab. Files: the
// project's tree and its Git section. A click opens the preview.
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { town } from "../link.js";
import { board, track, OPS, useOps } from "../board/store.js";
import { Today, needsCount } from "../board/today.js";
import { Goals, Ideas } from "../board/tracks.js";
import { Operations } from "../board/ops.js";
import { FilesPane } from "./files.js";
import { leftTab, refreshShell, openMap } from "./store.js";
import { projectsOn } from "./projects.js";

export function BoardPane() {
  const b = board.value, on = !projectsOn.value && leftTab.value === "files" ? "board" : leftTab.value;
  const count = b ? needsCount() : 0;
  const tabs = [["board", "Board"], ["needs", "Needs you"], ...(projectsOn.value ? [["files", "Files"]] : [])];
  useOps();
  // Needs you holds Operations' rows: the Board is read again when Operations moved.
  const rev = town.value?.ops_rev;
  useEffect(() => { if (rev) refreshShell(); }, [rev]);
  return html`<section class="shell-pane shell-board" aria-label=${on === "files" ? "Files" : on === "needs" ? "Needs you" : "Board"}>
    <header class="shell-pane__head shell-pane__tabs" role="tablist" aria-label=${tabs.map((t) => t[1]).join(", ")}>
      ${tabs.map(([id, name]) => html`<button key=${id} role="tab" aria-selected=${on === id}
        class=${cls("shell-ltab", { "is-on": on === id })} onClick=${() => { leftTab.value = id; }}>${name}${id === "needs" && count > 0 && html`<span class="shell-count ork-count warning">${count}</span>`}</button>`)}
    </header>
    <div class="shell-pane__body">
      ${on === "files" ? html`<${FilesPane} />`
        : !b ? html`<p class="ok-tone-muted">Opening the board…</p>`
        : on === "needs" ? html`<${Today} />`
        : html`<button class="ork-btn shell-mapbtn" title="Your goals, ideas and tasks on one screen" onClick=${openMap}>Map</button><${Goals} />${track.value === OPS ? html`<${Operations} />` : html`<${Ideas} />`}`}
    </div>
  </section>`;
}
