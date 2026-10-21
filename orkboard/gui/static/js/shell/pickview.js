// The drawer's Pick one (docs/specs/51-pick-one.md §6): a task made a few variants of one kind and waits. The ask, the variants large (four across at 1 440, fewer
// when the drawer is narrower), ← → between them, the note (*Say why, or what to change (it goes to <member>)*), and at the foot *Take B* (the one picked) and
// *None of them: make new ones*, which refuses without a note (*A note says what to change: write one first*). Sending answers `ideas.pick` with `via: "drawer"`;
// the tab then closes. What was picked and written is kept with the pick (picks.js `choices`), so the stop's card and the drawer are of one mind.
import { useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { WhoHead } from "../orkui.js";
import { ask, board } from "../board/store.js";
import { closePreview, refreshShell } from "./store.js";
import { Tiles, choiceOf, choose } from "../arena/picks.js";
import { NEEDS_NOTE, NONE, kindCount, manyWords, noteWords, rowOf, takeWords, variantOf } from "../arena/pickwords.js";

export function PickView({ p }) {
  const row = rowOf(board.value?.needs_you, p.slug, p.task), box = useRef();
  const [busy, setBusy] = useState(false), [refused, setRefused] = useState(false);
  if (!row) return html`<p class="ok-tone-muted">Opening…</p>`;
  const c = choiceOf(row), taken = variantOf(row, c.key), note = c.note.trim();
  const send = async (key) => {
    setBusy(true);
    const got = await ask("ideas.pick", { slug: row.slug, task: row.task, key, ...(note ? { note } : {}), via: "drawer" });
    setBusy(false);
    if (!got?.ok) return;                                  // a refusal is toasted in the host's words; the drawer stays
    closePreview();
    await refreshShell();
  };
  const none = () => {                                      // asking for new ones says what to change: the note first
    if (!note) { setRefused(true); box.current?.focus(); return; }
    send(null);
  };
  return html`<div class="shell-result shell-pickone" data-media=${row.media}>
    <div class="shell-result__body">
      <header class="shell-pickone__head">
        <span class="arena-lbl">Pick one</span>
        <h2>${row.title}</h2>
        <p class="arena-cap shell-pickone__by">${row.by?.head && html`<${WhoHead} head=${row.by.head} small=${true} />`}<span>made by ${row.by?.name || "a member"} · ${kindCount(row)}${row.round > 1 ? ` · round ${row.round}` : ""}</span></p>
      </header>
      <p class="shell-pickone__ask">“${row.ask}”</p>
      <${Tiles} row=${row} big=${true} />
      <textarea ref=${box} class="ork-field shell-pickone__note" rows="3" value=${c.note} aria-label="Note" placeholder=${noteWords(row.by)}
        onInput=${(e) => { choose(row, { note: e.target.value }); if (refused && e.target.value.trim()) setRefused(false); }}></textarea>
      ${refused && html`<p class="ok-tone-error shell-pickone__refused" role="alert">${NEEDS_NOTE}</p>`}
    </div>
    <footer class="shell-result__foot shell-pickone__foot">
      <button type="button" class="ork-btn primary" disabled=${!taken || busy} title=${taken ? `Goes on with ${c.key} · ${taken.name}` : `Pick one of the ${manyWords(row)} first`}
        onClick=${() => send(taken.key)}>${takeWords(c.key)}</button>
      <button type="button" class="ork-btn" disabled=${busy} title=${`New ${manyWords(row)} are made, with your note`} onClick=${none}>${NONE}</button>
    </footer>
  </div>`;
}
