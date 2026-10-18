// The Target chip (docs/specs/35-goals-window.md §1, §11.1): the Board's one setting, shown as "Target: Balance"; it
// opens the three with one line each. One per Board, for the whole route board → pool → gate.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { board } from "./store.js";
import { act } from "../shell/store.js";

export const TARGETS = [
  ["thrift", "Thrift", "lighter models, less reasoning, no proposals at night"],
  ["balance", "Balance", "the default: each step on the tier it needs"],
  ["quality", "Quality", "heavier models, more reasoning, three proposals a night"],
];

export function TargetChip() {
  const [open, setOpen] = useState(false);
  const now = board.value?.target || "balance";
  const word = (TARGETS.find(([id]) => id === now) || TARGETS[1])[1];
  const pick = async (id) => { setOpen(false); if (id !== now) await act("ideas.board_set", { target: id }); };
  return html`<div class="board-target">
    <button type="button" class="ok-btn board-target__chip" aria-haspopup="menu" aria-expanded=${open}
      title=${say("The Target picks every step's model and reasoning")} onClick=${() => setOpen(!open)}>Target: ${word}</button>
    ${open && html`<div class="board-target__menu kit-well" role="menu" aria-label="Target"
      onKeyDown=${(e) => { if (e.key === "Escape") { e.stopPropagation(); setOpen(false); } }}>
      ${TARGETS.map(([id, name, line]) => html`<button type="button" key=${id} role="menuitemradio" aria-checked=${id === now}
        class="board-target__one" data-target=${id} onClick=${() => pick(id)}><b>${name}</b><span class="ok-tone-muted">${line}</span></button>`)}
    </div>`}
  </div>`;
}
