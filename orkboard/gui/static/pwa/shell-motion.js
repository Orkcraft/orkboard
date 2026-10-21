// The phone's motion (docs/specs/49-one-window.md §11): it says what changed, never decorates. Each in steps or a short ease, none under `prefers-reduced-motion`, none on the
// first read of a goal, none for what changed while the page was hidden. Ticking words (*working 4 min*) and counts never move. The pieces the field (shell-arena-field.js)
// uses: a task that moves in its column or settles into a gap left by one that left slides from where it stood (FLIP: each item's old box measured before the redraw, its new
// one after, the difference played back); nothing moves under the finger or the focus (a column's redraw waits, at most 10 s); a number that a merge changed shows its new value
// with a one-time highlight.
const SLIDE_MS = 250;                                 // a settle or a move, ease-out, no bounce
const PULSE_MS = 600;                                 // the reward's highlight
export const HOLD_MS = 10000;                         // a column is held under a touch or the focus for at most this long

/** Whether the page may move now: not under reduced motion, not while it is hidden. */
export const motionOn = () => !document.hidden && !(typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches);

/** Where each item of each column stands: `column|key` → its top below its column's head, where the member stands (the page above it left out). */
export function measure(root) {
  const where = new Map();
  for (const col of root.querySelectorAll(".stack[data-column]")) {
    const head = col.getBoundingClientRect().top;
    for (const item of col.querySelectorAll("[data-key]")) where.set(`${col.dataset.column}|${item.dataset.key}`, item.getBoundingClientRect().top - head);
  }
  return where;
}

/** The difference between what `measure` saw and where the items stand now, played back (≈ 0.25 s, ease-out): only the items that moved move. */
export function play(root, before) {
  for (const col of root.querySelectorAll(".stack[data-column]")) {
    const head = col.getBoundingClientRect().top;
    for (const item of col.querySelectorAll("[data-key]")) {
      const was = before.get(`${col.dataset.column}|${item.dataset.key}`);
      if (was === undefined) continue;                // new here: it rises on its own
      const dy = was - (item.getBoundingClientRect().top - head);
      if (Math.abs(dy) > 1 && item.animate) item.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: SLIDE_MS, easing: "ease-out" });
    }
  }
}

/** Takes `gone` (items) out of their column and lets the queue behind them step up toward the member into the gap. */
export function settle(gone) {
  const cols = new Set(gone.map((g) => g.parentElement).filter(Boolean));
  const before = new Map();
  for (const col of cols) for (const el of col.children) before.set(el, el.getBoundingClientRect().top);
  for (const g of gone) g.remove();
  for (const col of cols) {
    for (const el of col.children) {
      const dy = before.get(el) - el.getBoundingClientRect().top;
      if (Math.abs(dy) > 1 && el.animate) el.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: SLIDE_MS, easing: "ease-out" });
    }
  }
}

/** A number that a merge changed: its new value shown with a one-time highlight (the class animates in steps; none under reduced motion, by the sheet). */
export function pulse(el) {
  if (!el) return;
  el.classList.remove("is-reward");
  void el.offsetWidth;                                // the animation starts again when a second merge follows the first
  el.classList.add("is-reward");
  setTimeout(() => el.classList.remove("is-reward"), PULSE_MS + 50);
}

/** True while the field is being drawn again: a focus that leaves because its node was replaced is not a person's moving on (`makeHolds` ignores it). */
export const painting = { on: false };
const IDENT = ["goal", "band", "member", "key", "idea", "task", "act"];

/** Runs `paint` (which draws again what `root` holds) and puts the focus back on what had it, so that a keyboard's place survives a refresh: the same node when it is still
 *  there, else the one that stands for it (the same tag and the same `data-*`). */
export function keepFocus(root, paint) {
  const a = document.activeElement;
  const had = a && a !== document.body && root.contains(a) ? { node: a, tag: a.tagName.toLowerCase(), cls: (a.className || "").toString().split(" ")[0], ids: IDENT.filter((k) => a.dataset[k] !== undefined).map((k) => [k, a.dataset[k]]) } : null;
  painting.on = true;
  try { paint(); } finally { painting.on = false; }
  if (!had) return;
  let at = had.node.isConnected ? had.node : null;
  if (!at) {
    const sel = had.tag + (had.ids.length ? had.ids.map(([k, v]) => `[data-${k}="${CSS.escape(v)}"]`).join("") : had.cls ? `.${CSS.escape(had.cls)}` : "");
    try { at = root.querySelector(sel); } catch { at = null; }
  }
  if (at && document.activeElement !== at) at.focus({ preventScroll: true });
}

/** Nothing moves under the finger or the focus: `held(column)` is true while a touch is down in the column or the focus (the keyboard's) is inside it, for at most HOLD_MS.
 *  `redraw` runs when a hold ends, and only when a redraw was held back (`deferred`: set when `held` said yes, cleared by the redraw that began with `begin()`): a focus that
 *  moves because the person pressed something is no reason to draw the field again. `root`: what holds the columns. */
export function makeHolds(root, redraw) {
  const touching = new Set();                         // the columns with a touch down
  const began = new Map();                            // the column → when its hold began
  let waiting = 0;
  let deferred = false;                               // a draw was held back since the last one began
  const column = (e) => e.target.closest?.(".stack[data-column]");
  const release = () => { if (deferred && !waiting) waiting = setTimeout(() => { waiting = 0; redraw(); }, 0); };
  root.addEventListener("touchstart", (e) => { const c = column(e); if (c) touching.add(c.dataset.column); }, { passive: true });
  for (const type of ["touchend", "touchcancel"]) root.addEventListener(type, () => { if (touching.size) { touching.clear(); release(); } }, { passive: true });
  root.addEventListener("focusout", () => { if (!painting.on) release(); });
  return {
    /** A draw begins: nothing it held back before is waiting any more (the columns it holds now say so again). */
    begin() { deferred = false; },
    held(col) {
      const key = col.dataset.column;
      if (!touching.has(key) && !col.querySelector(":focus-visible")) { began.delete(key); return false; }
      if (!began.has(key)) { began.set(key, Date.now()); setTimeout(redraw, HOLD_MS + 50); }
      const yes = Date.now() - began.get(key) <= HOLD_MS;
      if (yes) deferred = true;
      return yes;
    },
  };
}

/** No lost tap (docs/specs/50-parties-and-goals.md §6.9): a press is a `pointerdown` and a `pointerup` with the click after them, and a redraw between them removes the node the
 *  click was meant for. While a pointer is down on one of `roots` (captured: before the focus moves), `waits()` says true and keeps that a draw is wanted (`pending`; the caller does
 *  not use up its signature); after `pointerup` or `pointercancel`, in a 0 ms timeout (the click lands first), `redraw` runs once for what was postponed. A pointer that never comes
 *  up (HOLD_MS) does not keep the field from drawing. */
export function pointerGuard(roots, redraw) {
  let down = 0;                                       // when the pointer went down (0: none)
  let pending = false;
  const up = () => {
    if (!down) return;
    setTimeout(() => { down = 0; if (pending) { pending = false; redraw(); } }, 0);
  };
  for (const root of [roots].flat()) root.addEventListener("pointerdown", () => { down = Date.now(); }, true);
  window.addEventListener("pointerup", up, true);
  window.addEventListener("pointercancel", up, true);
  return {
    /** True while a pointer is down: the draw is postponed (and runs after it comes up). */
    waits() {
      if (!down || Date.now() - down > HOLD_MS) return false;
      pending = true;
      return true;
    },
  };
}
