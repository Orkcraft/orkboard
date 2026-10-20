// The left column (docs/specs/33-v1-shell.md §6, spec 35 §11, spec 37 §8), its screens split as the phone's: Board · Files (Needs you,
// with Review, is the right column: spec 46 §6.3). The Board: the goal shown (the select, with New goal and the Target; its card: its party's heads, its line, how far its
// ideas are), then that goal's ideas with New idea at their head. Files: the
// project's tree and its Git section. A click opens the preview.
import { useEffect } from "preact/hooks";
import { html, cls } from "../html.js";
import { town } from "../link.js";
import { board, track, OPS, useOps } from "../board/store.js";
import { Goals, Ideas } from "../board/tracks.js";
import { Operations } from "../board/ops.js";
import { FilesPane } from "./files.js";
import { leftTab, refreshShell, openMap } from "./store.js";
import { projectsOn } from "./projects.js";

export function BoardPane() {
  const b = board.value, on = leftTab.value === "files" && projectsOn.value ? "files" : "board";   // a "needs" kept from before reads "board"
  const tabs = [["board", "Board"], ...(projectsOn.value ? [["files", "Files"]] : [])];
  useOps();
  // Needs you (the right column) holds Operations' rows: the Board is read again when Operations moved.
  const rev = town.value?.ops_rev;
  useEffect(() => { if (rev) refreshShell(); }, [rev]);
  return html`<section class="shell-pane shell-board" aria-label=${on === "files" ? "Files" : "Board"}>
    <header class="shell-pane__head shell-pane__tabs" role="tablist" aria-label=${tabs.map((t) => t[1]).join(", ")}>
      ${tabs.map(([id, name]) => html`<button key=${id} role="tab" aria-selected=${on === id}
        class=${cls("shell-ltab", { "is-on": on === id })} onClick=${() => { leftTab.value = id; }}>${name}</button>`)}
    </header>
    <div class="shell-pane__body">
      ${on === "files" ? html`<${FilesPane} />`
        : !b ? html`<p class="ok-tone-muted">Opening the board…</p>`
        : html`<button class="ork-btn shell-mapbtn" title="Your goals, ideas and tasks on one screen" onClick=${openMap}>Map</button><${Goals} />${track.value === OPS ? html`<${Operations} />` : html`<${Ideas} />`}`}
    </div>
  </section>`;
}
