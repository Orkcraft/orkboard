// A designer's lens on the phone (realm/idea_lens.py): a screen of the app — one the project keeps, or a new picture (the camera
// or the library, made a JPEG as a photo is) — with areas marked on it: a finger drawn across the picture marks a box, and each
// box gets a line saying what to change there. The marks are kept as parts of the picture (0 to 1 from its top left corner).
import { h } from "./util.js";
import { shrink } from "./shell-idea-field.js";

const MIN = 0.02;                      // a box smaller than this, across or down, is a slip: no mark
const MAX_MARKS = 8;                   // realm/idea_lens.py MAX_MARKS

/** `core`: the board's frame (its `call`); `ctx`: {flash}. Returns {el, load(screens), value(), reset()}. */
export function makeScreenLens(core, ctx) {
  let kept = [];                       // the project's screens: [{id, name}]
  let chosen = null;                   // {id} a kept one, or {url, name} a new picture
  let marks = [];                      // [{x, y, w, h, note}]
  const pick = h("input", { type: "file", accept: "image/*", hidden: true, "aria-label": "A screen to mark" });
  const name = h("input", { class: "ork-field", type: "text", maxlength: "60", "aria-label": "The screen's name", placeholder: "Its name: Settings, Checkout…" });
  const img = h("img", { class: "lens-shot", alt: "The screen", draggable: "false" });
  const stage = h("div", { class: "lens-stage", hidden: true }, img);
  const list = h("ol", { class: "lens-marks", "aria-label": "Marks" });
  const shelf = h("div", { class: "lens-screens", role: "group", "aria-label": "The project's screens" });
  const nameRow = h("div", { class: "field", hidden: true }, h("span", { class: "field-label" }, "Name"), name);
  const hint = h("p", { class: "muted lens-hint" }, "Draw a box across what to change, then say what in its line.");

  function drawShelf() {
    shelf.replaceChildren(...kept.map((s) => h("button", { class: "ork-btn lens-screen", type: "button", "aria-pressed": String(chosen?.id === s.id),
      onclick: () => choose({ id: s.id }) }, s.name)),
    h("button", { class: "ork-btn", type: "button", onclick: () => pick.click() }, kept.length ? "Another screen" : "Add a screen"), pick);
  }

  async function choose(c) {
    chosen = c;
    marks = [];
    nameRow.hidden = !c.url;
    if (c.url) img.src = c.url;
    else {
      const got = await core.call("ideas.lens_screen", { id: c.id });
      if (!got || chosen !== c) return;
      img.src = `data:${got.type};base64,${got.data}`;
    }
    stage.hidden = false;
    drawShelf();
    drawMarks();
  }

  pick.addEventListener("change", async () => {
    const f = pick.files?.[0];
    pick.value = "";
    if (!f) return;
    try { await choose({ url: await shrink(f) }); name.focus(); } catch { ctx.flash("That picture could not be read: try another."); }
  });

  function box(m, n) {
    const el = h("span", { class: "lens-mark", "aria-hidden": "true" }, h("b", {}, String(n)));
    Object.assign(el.style, { left: `${m.x * 100}%`, top: `${m.y * 100}%`, width: `${m.w * 100}%`, height: `${m.h * 100}%` });
    return el;
  }
  function drawMarks() {
    stage.replaceChildren(img, ...marks.map((m, i) => box(m, i + 1)));
    list.replaceChildren(...marks.map((m, i) => {
      const note = h("input", { class: "ork-field", type: "text", maxlength: "300", value: m.note, "aria-label": `Mark ${i + 1}: what to change`, placeholder: "What to change here" });
      note.addEventListener("input", () => { m.note = note.value; });
      return h("li", {}, h("b", {}, `${i + 1}`), note,
        h("button", { class: "ork-btn", type: "button", "aria-label": `Remove mark ${i + 1}`, onclick: () => { marks.splice(i, 1); drawMarks(); } }, "×"));
    }));
  }

  // -- drawing: a finger (or the mouse) across the picture marks a box ----------------------------------------------------
  let start = null, live = null;
  const at = (e) => {
    const r = img.getBoundingClientRect();
    return { x: Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)), y: Math.min(1, Math.max(0, (e.clientY - r.top) / r.height)) };
  };
  const span = (a, b) => ({ x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) });
  stage.addEventListener("pointerdown", (e) => {
    if (marks.length >= MAX_MARKS) { ctx.flash(`At most ${MAX_MARKS} marks on a screen.`); return; }
    e.preventDefault();
    stage.setPointerCapture?.(e.pointerId);
    start = at(e);
    live = box({ ...start, w: 0, h: 0 }, marks.length + 1);
    stage.append(live);
  });
  stage.addEventListener("pointermove", (e) => {
    if (!start) return;
    const m = span(start, at(e));
    Object.assign(live.style, { left: `${m.x * 100}%`, top: `${m.y * 100}%`, width: `${m.w * 100}%`, height: `${m.h * 100}%` });
  });
  const end = (e) => {
    if (!start) return;
    const m = span(start, at(e));
    start = null;
    live?.remove();
    if (m.w >= MIN && m.h >= MIN) {
      marks.push({ ...m, note: "" });
      drawMarks();
      list.querySelector("li:last-child input")?.focus();
    }
  };
  stage.addEventListener("pointerup", end);
  stage.addEventListener("pointercancel", () => { start = null; live?.remove(); });

  const el = h("div", { class: "lens-screen-pane" }, shelf, nameRow, stage, hint, list);
  return {
    el,
    load(screens) { kept = screens || []; drawShelf(); },
    /** What `ideas.add` takes in `lens` ([] with no screen chosen). */
    value() {
      if (!chosen) return [];
      const r4 = (v) => Math.round(v * 10000) / 10000;
      const mk = marks.map((m) => ({ x: r4(m.x), y: r4(m.y), w: r4(m.w), h: r4(m.h), note: m.note.trim() }));
      return [chosen.url ? { kind: "screen", image: { data: chosen.url.slice(chosen.url.indexOf(",") + 1) }, name: name.value.trim(), marks: mk }
        : { kind: "screen", screen: chosen.id, marks: mk }];
    },
    reset() { chosen = null; marks = []; name.value = ""; img.removeAttribute("src"); stage.hidden = true; nameRow.hidden = true; drawShelf(); drawMarks(); },
  };
}
