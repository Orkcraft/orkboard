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

/** Where each item of each column stands: `column|key` → its top above its column's foot (the column's own scroll and the page above it left out). */
export function measure(root) {
  const where = new Map();
  for (const col of root.querySelectorAll(".stack[data-column]")) {
    const foot = col.getBoundingClientRect().bottom;
    for (const item of col.querySelectorAll("[data-key]")) where.set(`${col.dataset.column}|${item.dataset.key}`, item.getBoundingClientRect().top - foot);
  }
  return where;
}

/** The difference between what `measure` saw and where the items stand now, played back (≈ 0.25 s, ease-out): only the items that moved move. */
export function play(root, before) {
  for (const col of root.querySelectorAll(".stack[data-column]")) {
    const foot = col.getBoundingClientRect().bottom;
    for (const item of col.querySelectorAll("[data-key]")) {
      const was = before.get(`${col.dataset.column}|${item.dataset.key}`);
      if (was === undefined) continue;                // new here: it rises on its own
      const dy = was - (item.getBoundingClientRect().top - foot);
      if (Math.abs(dy) > 1 && item.animate) item.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: SLIDE_MS, easing: "ease-out" });
    }
  }
}

/** Takes `gone` (items) out of their column and lets what they held up slide down into the gap. */
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

/** Nothing moves under the finger or the focus: `held(column)` is true while a touch is down in the column or the focus (the keyboard's) is inside it, for at most HOLD_MS.
 *  `redraw` runs when a hold ends. `root`: what holds the columns. */
export function makeHolds(root, redraw) {
  const touching = new Set();                         // the columns with a touch down
  const began = new Map();                            // the column → when its hold began
  let waiting = 0;
  const column = (e) => e.target.closest?.(".stack[data-column]");
  const release = () => { if (!waiting) waiting = setTimeout(() => { waiting = 0; redraw(); }, 0); };
  root.addEventListener("touchstart", (e) => { const c = column(e); if (c) touching.add(c.dataset.column); }, { passive: true });
  for (const type of ["touchend", "touchcancel"]) root.addEventListener(type, () => { if (touching.size) { touching.clear(); release(); } }, { passive: true });
  root.addEventListener("focusout", () => release());
  return {
    held(col) {
      const key = col.dataset.column;
      if (!touching.has(key) && !col.querySelector(":focus-visible")) { began.delete(key); return false; }
      if (!began.has(key)) { began.set(key, Date.now()); setTimeout(redraw, HOLD_MS + 50); }
      return Date.now() - began.get(key) <= HOLD_MS;
    },
  };
}
