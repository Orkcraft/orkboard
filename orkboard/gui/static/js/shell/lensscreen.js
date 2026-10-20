// A designer's lens on the desktop, as the phone's (pwa/shell-lens-screen.js): a screen of the app — one the project keeps, or a
// new picture — with areas marked on it: the mouse drawn across the picture marks a box, and each box gets a line saying what to
// change there. The marks are kept as parts of the picture (0 to 1 from its top left corner).
import { useRef, useState } from "preact/hooks";
import { html } from "../html.js";
import { toast } from "../link.js";
import { ask } from "../board/store.js";

const MIN = 0.02;                      // a box smaller than this, across or down, is a slip: no mark
const MAX_MARKS = 8;                   // realm/idea_lens.py MAX_MARKS
const MAX_PX = 1600;

/** A picture as a JPEG data URL of at most MAX_PX on its longer side (as the phone's shrink). */
async function shrink(file) {
  const url = await new Promise((ok, fail) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = fail; r.readAsDataURL(file); });
  const img = new Image();
  img.src = url;
  await img.decode();
  const k = Math.min(1, MAX_PX / Math.max(img.naturalWidth, img.naturalHeight));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.naturalWidth * k);
  canvas.height = Math.round(img.naturalHeight * k);
  canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.8);
}

const place = (m) => `left:${m.x * 100}%;top:${m.y * 100}%;width:${m.w * 100}%;height:${m.h * 100}%`;
const span = (a, b) => ({ x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) });

/** The screen lens's state, kept by the dialog: {chosen, src, name, marks}. */
export const noScreen = { chosen: null, src: "", name: "", marks: [] };

/** What `ideas.add` takes in `lens` for the screen ([] with none chosen). */
export function screenValue(s) {
  if (!s.chosen) return [];
  const r4 = (v) => Math.round(v * 10000) / 10000;
  const marks = s.marks.map((m) => ({ x: r4(m.x), y: r4(m.y), w: r4(m.w), h: r4(m.h), note: m.note.trim() }));
  return [s.chosen.url ? { kind: "screen", image: { data: s.chosen.url.slice(s.chosen.url.indexOf(",") + 1) }, name: s.name.trim(), marks }
    : { kind: "screen", screen: s.chosen.id, marks }];
}

export function ScreenLens({ kept, value, set }) {
  const shot = useRef(), pick = useRef();
  const [live, setLive] = useState(null);           // the box being drawn
  const start = useRef(null);
  const choose = async (c) => {
    if (c.url) { set({ chosen: c, src: c.url, name: "", marks: [] }); return; }
    set({ ...noScreen, chosen: c });
    const got = await ask("ideas.lens_screen", { id: c.id });
    if (got) set({ chosen: c, src: `data:${got.type};base64,${got.data}`, name: "", marks: [] });
  };
  const add = async (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    try { await choose({ url: await shrink(f) }); } catch { toast("That picture could not be read: try another.", "warning"); }
  };
  const at = (e) => {
    const r = shot.current.getBoundingClientRect();
    return { x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)) };
  };
  const down = (e) => {
    if (value.marks.length >= MAX_MARKS) { toast(`At most ${MAX_MARKS} marks on a screen.`, "warning"); return; }
    e.preventDefault();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    start.current = at(e);
    setLive({ ...start.current, w: 0, h: 0 });
  };
  const move = (e) => { if (start.current) setLive(span(start.current, at(e))); };
  const up = (e) => {
    if (!start.current) return;
    const m = span(start.current, at(e));
    start.current = null;
    setLive(null);
    if (m.w >= MIN && m.h >= MIN) set({ ...value, marks: [...value.marks, { ...m, note: "" }] });
  };
  const note = (i, text) => set({ ...value, marks: value.marks.map((m, j) => (j === i ? { ...m, note: text } : m)) });
  const drop = (i) => set({ ...value, marks: value.marks.filter((_, j) => j !== i) });
  return html`<div class="shell-lens-screen">
    <div class="shell-lens-screens" role="group" aria-label="The project's screens">
      ${kept.map((s) => html`<button key=${s.id} type="button" class="ork-btn shell-lens-pick" aria-pressed=${String(value.chosen?.id === s.id)}
        onClick=${() => choose({ id: s.id })}>${s.name}</button>`)}
      <button type="button" class="ork-btn" onClick=${() => pick.current.click()}>${kept.length ? "Another screen" : "Add a screen"}</button>
      <input ref=${pick} type="file" accept="image/*" hidden aria-label="A screen to mark" onChange=${add} /></div>
    ${value.chosen?.url && html`<label class="shell-field"><span class="ok-font-label">Name</span>
      <input class="ork-field" maxlength="60" value=${value.name} aria-label="The screen's name" placeholder="Its name: Settings, Checkout…"
        onInput=${(e) => set({ ...value, name: e.target.value })} /></label>`}
    ${value.src && html`<div class="shell-lens-stage" onPointerDown=${down} onPointerMove=${move} onPointerUp=${up}
        onPointerCancel=${() => { start.current = null; setLive(null); }}>
      <img ref=${shot} class="shell-lens-shot" src=${value.src} alt="The screen" draggable="false" />
      ${value.marks.map((m, i) => html`<span key=${i} class="shell-lens-mark" style=${place(m)} aria-hidden="true"><b>${i + 1}</b></span>`)}
      ${live && html`<span class="shell-lens-mark" style=${place(live)} aria-hidden="true"><b>${value.marks.length + 1}</b></span>`}</div>
      <p class="ok-font-status ok-tone-muted">Draw a box across what to change, then say what in its line.</p>`}
    ${value.marks.length > 0 && html`<ol class="shell-lens-marks" aria-label="Marks">${value.marks.map((m, i) => html`<li key=${i}><b>${i + 1}</b>
      <input class="ork-field" maxlength="300" value=${m.note} aria-label=${`Mark ${i + 1}: what to change`} placeholder="What to change here"
        onInput=${(e) => note(i, e.target.value)} />
      <button type="button" class="ork-btn" aria-label=${`Remove mark ${i + 1}`} onClick=${() => drop(i)}>×</button></li>`)}</ol>`}
  </div>`;
}
