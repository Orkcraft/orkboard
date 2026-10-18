// The Board pane, on the left (docs/specs/33-v1-shell.md §6, spec 35 §11): the goal select with New goal and the Target,
// Needs you (one list), then the ideas with New idea at their head. A click opens the preview.
import { html } from "../html.js";
import { board } from "../board/store.js";
import { Today } from "../board/today.js";
import { Goals, Ideas } from "../board/tracks.js";

export function BoardPane() {
  const b = board.value;
  return html`<section class="shell-pane shell-board" aria-label="Board">
    <header class="shell-pane__head"><h2>Board</h2></header>
    <div class="shell-pane__body">
      ${b ? html`<${Goals} /><${Today} /><${Ideas} />` : html`<p class="ok-tone-muted">Opening the board…</p>`}
    </div>
  </section>`;
}
