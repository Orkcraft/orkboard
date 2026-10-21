// The foot of the right column (docs/specs/42-coming-back.md §2.4, docs/specs/50-parties-and-goals.md §3.3): *Last week*. The goals' flags are not here
// any more: a goal's flag is its own (arena/goals.js, the Flags fold of the party's goals) and the party's old flags are *Before:* in About this party.
import { html } from "../html.js";
import { showWeek } from "../shell/look.js";

export function MapFoot() {
  return html`<div class="map-foot">
    <button type="button" class="board-link map-foot__week" onClick=${showWeek}>Last week</button>
  </div>`;
}
