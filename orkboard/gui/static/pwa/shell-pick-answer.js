// Pick one on the phone, the answer (docs/specs/51-pick-one.md §0, §2.3, §7): what the person did with a pick's tiles — the letter picked, a note — and the two ways to answer, *Take B* and
// *None of them: make new ones* (the note first; *A note says what to change: write one first*). The same panel is the raised stop's (`via: "hand"`, tiles 2 × 2) and the pick's own screen's
// (`via: "screen"`, one tile to a screen); what was picked and typed on the one is there on the other, until the pick is answered. The words come from §0; the command is `ideas.pick`.
import { h } from "./util.js";
import { whoHead } from "./shell-who.js";
import { tiles, labelOf, countWords } from "./shell-picks.js";

export const NEEDS_NOTE = "A note says what to change: write one first";
const NOTE_MAX = 2000;
const drafts = new Map();                            // `slug/task-rN` → {key, note}: kept across a redraw, a lowered card and the card's own screen

const idOf = (row) => `${row.slug}/${row.task}-r${row.round}`;
/** What the person picked and typed for this round of this pick so far. */
export function draftOf(row) {
  const id = idOf(row);
  if (!drafts.has(id)) drafts.set(id, { key: "", note: "" });
  return drafts.get(id);
}
/** The picks that wait now: a draft of any other is let go. */
export function forget(rows) {
  const keep = new Set(rows.map(idOf));
  for (const id of [...drafts.keys()]) if (!keep.has(id)) drafts.delete(id);
}

/** The tiles, the note and the two answers of one pick. `core`: the board's frame (call, refresh); `ctx`: {flash}; `via`: where it is answered (`hand`, `screen`); `after()`: what follows an
 *  answer that went through (the card is put back, the screen is left); `swipe`: the tiles one to a screen. Returns {tiles, note, say, take, none, group}. */
export function makePanel(core, ctx, row, { via, after, swipe = false }) {
  const d = draftOf(row), who = row.by?.name || "Grunt";
  let busy = false;
  const say = h("p", { class: "warn pk__say", role: "alert", hidden: true });
  const group = tiles(row, { picked: d.key, large: swipe, swipe, onPick: (k) => { d.key = k; sync(); } });
  const note = h("textarea", { class: "ork-field pk__note", rows: "2", maxlength: String(NOTE_MAX), "aria-label": "Note", placeholder: `Say why, or what to change (it goes to ${who})` });
  note.value = d.note;
  note.addEventListener("input", () => { d.note = note.value; tell(""); });
  const take = h("button", { class: "ork-btn primary", type: "button", "data-act": "take" });
  const none = h("button", { class: "ork-btn", type: "button", "data-act": "none" }, "None of them: make new ones");

  function tell(text) {
    say.textContent = text;
    say.hidden = !text;
    note.setAttribute("aria-invalid", text === NEEDS_NOTE ? "true" : "false");
  }
  function sync() {
    const v = (row.variants || []).find((x) => x.key === d.key);
    take.disabled = busy || !v;
    take.textContent = v ? `Take ${v.key}` : "Take the one you pick";
    take.title = v ? `Goes on with ${labelOf(v)}` : `Pick one of the ${countWords(row.variants?.length || 0, row.media)} first`;
    none.disabled = busy;
    none.title = "Asks for new ones: the note says what to change";
  }
  /** Answers with a letter, or with none (`key` null: a note is required, said before anything is sent). */
  async function send(key) {
    const text = d.note.trim();
    if (key === null && !text) { tell(NEEDS_NOTE); note.focus(); return; }
    tell("");
    busy = true;
    sync();
    const r = await core.call("ideas.pick", { slug: row.slug, task: row.task, key, ...(text ? { note: text } : {}), via }, tell);      // an error is said here: a toast lies under the card
    busy = false;
    sync();
    if (!r) return;
    drafts.delete(idOf(row));
    ctx.flash(key ? `Picked ${key}.` : "New ones asked.");
    after();
  }
  take.addEventListener("click", () => d.key && send(d.key));
  none.addEventListener("click", () => send(null));
  sync();
  return { tiles: group.el, note, say, take, none, group };
}

/** The pick's own screen: who made them and for which ask, the tiles one to a screen (swiped, with their dots), then the note and the same two answers under them (`via: "screen"`). */
export function screenBody(core, ctx, row) {
  const panel = makePanel(core, ctx, row, { via: "screen", swipe: true, after: () => { core.refresh(); core.close(); } });
  requestAnimationFrame(() => panel.group.reveal());
  return [
    h("div", { class: "pk-from" }, row.by?.head ? whoHead(row.by.head, false) : null, h("span", { class: "muted" }, `${row.by?.name || "Grunt"} · ${countWords(row.n ?? row.variants.length, row.media)}${row.round > 1 ? ` · round ${row.round}` : ""}`)),
    h("p", { class: "pk-ask" }, `“${row.ask}”`),
    panel.tiles, panel.group.pips,
    panel.note, panel.say, panel.take, panel.none,
  ];
}
