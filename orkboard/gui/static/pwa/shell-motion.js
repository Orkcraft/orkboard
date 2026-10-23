// The phone's motion (docs/specs/49-one-window.md §11, spec 50 §4): it says what changed, never decorates. Each in steps or a short ease, none under `prefers-reduced-motion`, none on the
// first read of a goal, none for what changed while the page was hidden. Ticking words (*working 4 min*) and counts never move. The pieces the field (shell-arena-field.js)
// uses: a task that moves in its column or settles into a gap left by one that left slides from where it stood (FLIP: each item's old box measured before the redraw, its new
// one after, the difference played back); nothing moves under the finger or the focus (a column's redraw waits, at most 10 s); a number that a merge changed shows its new value
// with a one-time highlight. Three moments travel, the three decisions §76.3 allows: the deal (a plan started from the hand deals its tasks onto the field, spec 57), the gather (a new party's
// heads gather into its deck, spec 63 §4) and the flags raised (their goals' elements travel from the gate to the flag line, spec 64); each over the page, in steps, 0.30 s and 35 ms apart, six at most.
const SLIDE_MS = 250;                                 // a settle or a move, ease-out, no bounce
const PULSE_MS = 600;                                 // the reward's highlight
export const HOLD_MS = 10000;                         // a column is held under a touch or the focus for at most this long
const DEAL_WAIT_MS = 6000;                            // a deal waits this long for the tasks of the plan it started (spec 57 §1.2)
const DEAL_STEP_MS = 35, DEAL_LEN_MS = 300, DEAL_MAX = 6;       // the deal: each card steps(6) for 0.30 s, 35 ms after the one before, six at most (spec 57 §2)
const LIT_MS = 600;                                   // a one-time highlight (`pulse`), as the quiet reward's

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

/** Takes `gone` (stacks that left) out of their columns and lets what lies behind them step up toward the member into the gap: the stacks and the count at the far end (a row by phase that has nothing
 *  left goes with them). */
export function settle(gone) {
  const cols = new Set(gone.map((g) => g.closest(".stack")).filter(Boolean));
  const movers = (col) => [...col.querySelectorAll(".deck:not(.is-leaving), .stack__done")];
  const before = new Map();
  for (const col of cols) for (const item of movers(col)) before.set(item, item.getBoundingClientRect().top);
  const rows = new Set(gone.map((g) => g.parentElement));
  for (const g of gone) g.remove();
  for (const row of rows) if (row?.classList?.contains("phase") && !row.querySelector(".deck")) row.remove();
  for (const col of cols) {
    for (const item of movers(col)) {
      const dy = before.get(item) - item.getBoundingClientRect().top;
      if (Math.abs(dy) > 1 && item.animate) item.animate([{ transform: `translateY(${dy}px)` }, { transform: "none" }], { duration: SLIDE_MS, easing: "ease-out" });
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

// -- the deal (docs/specs/57-deal-on-start.md §1, §2, §4) --------------------------------------------------------------------------------------------
/** The deal waiting: a plan started by a press on its raised stop deals its tasks from that card's box onto the stage shown. One at a time; dropped when played, refused or after 6 s. */
let waiting = null;
export const deal = {
  /** The press was answered ok: `goal` (the plan's goal slug) deals from `from` (the raised card's client rect at the press). */
  wait(goal, from) { waiting = from && from.width > 0 ? { goal, from, at: Date.now() } : null; },
  drop() { waiting = null; },
  /** The deal waiting (null once it is 6 s old). */
  live() {
    if (waiting && Date.now() - waiting.at > DEAL_WAIT_MS) waiting = null;
    return waiting;
  },
};

/** Deals `nodes` (the new stacks of the plan's goal in the field's order, already in the page) from the box `from`: each travels from the stop's centre, at the stop's width, to its own box,
 *  steps(6) 0.30 s, 35 ms after the one before, six at most. What travels is a copy over everything (the columns clip; the real stack lies hidden and lands when the copy does: it takes the
 *  pointer only then); a stack that is out of its column's view, and the stacks after the sixth, rise as they do without a deal. Returns how many travel. */
export function dealTo(nodes, from) {
  let k = 0;
  const cx = from.left + from.width / 2, cy = from.top + from.height / 2;
  for (const node of nodes) {
    const to = node.getBoundingClientRect(), clips = [node.closest(".arena-scroll"), node.closest(".stack")].filter(Boolean).map((c) => c.getBoundingClientRect());
    const seen = to.width > 0 && clips.every((c) => to.bottom > c.top && to.top < c.bottom && to.right > c.left && to.left < c.right);
    if (!seen) { node.classList.add("is-drawn"); continue; }
    if (k >= DEAL_MAX) { node.classList.add("is-drawn"); node.style.animationDelay = `${DEAL_MAX * DEAL_STEP_MS}ms`; continue; }       // after the sixth starts
    const vars = { "--dx": `${Math.round(cx - (to.left + to.width / 2))}px`, "--dy": `${Math.round(cy - (to.top + to.height / 2))}px`, "--s": String(Math.round((from.width / to.width) * 100) / 100),
      "--delay": `${k * DEAL_STEP_MS}ms` };
    for (const [name, value] of Object.entries(vars)) node.style.setProperty(name, value);
    node.classList.add("is-dealt");
    const fly = document.createElement("div");                           // the copy: the stack as it lies, in its phase's colours, over the page
    fly.className = `deal-fly phase is-${node.closest(".phase")?.dataset.phase || "now"}`;
    fly.setAttribute("aria-hidden", "true");
    Object.assign(fly.style, { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px` });
    for (const [name, value] of Object.entries(vars)) fly.style.setProperty(name, value);
    const copy = node.cloneNode(true);
    for (const a of ["data-key", "data-idea", "data-phase", "data-task", "data-state", "data-n", "title", "aria-label", "style"]) copy.removeAttribute(a);
    copy.classList.remove("is-dealt", "is-drawn");
    copy.tabIndex = -1;
    fly.append(copy);
    document.body.append(fly);
    setTimeout(() => fly.remove(), k * DEAL_STEP_MS + DEAL_LEN_MS + 120);
    k += 1;
  }
  return k;
}

// -- the flags raised (docs/specs/64-flags-raised.md §1, §2, §4) ----------------------------------------------------------------------------------------
const RAISE_WAIT_MS = 10000;                          // a raise waits this long for its line to be in view (the gate's screen lies over it right after a merge); the merge's box lives as long

/** The raise waiting: the flag line stands for the first time, so its goals' elements travel to it once, from the gate. One at a time; dropped when played, or after 10 s. */
let lifting = null;
export const raise = {
  /** The flag line stands for the first time (nothing waits under reduced motion or on a hidden page: it stands still). */
  wait() { lifting = motionOn() ? { at: Date.now() } : null; },
  drop() { lifting = null; },
  /** The raise waiting (null once it is 10 s old). */
  live() {
    if (lifting && Date.now() - lifting.at > RAISE_WAIT_MS) lifting = null;
    return lifting;
  },
};

/** Whether `el` is in view: it has a box inside the screen and the element at the box's centre is it or one of its own (the drawer, a sheet or a full screen over it make it not). */
export function inView(el) {
  const r = el?.isConnected ? el.getBoundingClientRect() : null;
  if (!r || r.width <= 0 || r.height <= 0) return false;
  const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return Boolean(top && el.contains(top));
}

/** Flies a copy of each of `slots` (the elements of the flag line's row, already in the page, in the line's order) from the box `from` to its place: from the box's centre, scaled from the box's
 *  height to its own, steps(6) 0.30 s, 35 ms after the one before (the deal's, as `dealTo`). The copy lies over everything and takes nothing; the slot lies hidden and shows when its copy lands.
 *  Returns the ms until the last has landed. */
export function raiseTo(slots, from) {
  const cx = from.left + from.width / 2, cy = from.top + from.height / 2;
  slots.forEach((slot, k) => {
    const to = slot.getBoundingClientRect();
    const vars = { "--dx": `${Math.round(cx - (to.left + to.width / 2))}px`, "--dy": `${Math.round(cy - (to.top + to.height / 2))}px`, "--s": String(Math.round((from.height / to.height) * 100) / 100),
      "--delay": `${k * DEAL_STEP_MS}ms` };
    const fly = slot.cloneNode(true);                                    // the copy: the element as it lies in the row, over the page
    fly.classList.add("flag-fly");
    fly.setAttribute("aria-hidden", "true");
    Object.assign(fly.style, { left: `${to.left}px`, top: `${to.top}px`, width: `${to.width}px`, height: `${to.height}px` });
    for (const [name, value] of Object.entries(vars)) { slot.style.setProperty(name, value); fly.style.setProperty(name, value); }
    slot.classList.add("is-dealt");
    document.body.append(fly);
    setTimeout(() => fly.remove(), k * DEAL_STEP_MS + DEAL_LEN_MS + 120);
  });
  return slots.length ? (slots.length - 1) * DEAL_STEP_MS + DEAL_LEN_MS : 0;
}

// -- the gather (docs/specs/63-party-gathered.md §4, decisions §76.2) -------------------------------------------------------------------------------------
const GATHER_SCALE = 0.4;                             // a head ends at the deck's centre at this part of its size
/** The gather waiting: a party saved on New party's sheet gathers its heads (`from`: [{race, tier, box}], the leader first, six at most, each box where the sheet showed that head at the press)
 *  into the party's deck, once the sheet has closed and the deck shows that party. One at a time; dropped when played, refused or after 6 s. */
let gathering = null;
export const gather = {
  /** How long the gather of `n` heads plays, to the end of the deck's light: what opens over the field after a save waits this long, so the deck is seen to take the party. */
  ms(n) { return n > 0 ? (Math.min(n, DEAL_MAX) - 1) * DEAL_STEP_MS + DEAL_LEN_MS + LIT_MS : 0; },
  /** The save was answered with `party`'s slug. */
  wait(party, from) { gathering = party && from?.length ? { party, from: from.slice(0, DEAL_MAX), at: Date.now() } : null; },
  drop() { gathering = null; },
  /** The gather waiting (null once it is 6 s old). */
  live() {
    if (gathering && Date.now() - gathering.at > DEAL_WAIT_MS) gathering = null;
    return gathering;
  },
};

/** Gathers the heads of `waiting` into its party's deck (`.partydeck`): each a copy over the page (nothing dims, nothing takes the pointer) from where the sheet showed it to the deck's centre at 0.4 of
 *  its size, steps(6) 0.30 s, 35 ms after the one before, gone on landing; when the last has landed the deck is lit once. Returns how many travel (none when the deck is not in the page). */
export function gatherTo(waiting) {
  const deckOf = () => document.querySelector(`.partydeck[data-goal="${CSS.escape(waiting.party)}"]`);
  const to = deckOf()?.getBoundingClientRect();
  if (!to || !(to.width > 0)) return 0;
  const cx = to.left + to.width / 2, cy = to.top + to.height / 2;
  const heads = waiting.from.slice(0, DEAL_MAX);
  heads.forEach(({ race, tier, box }, k) => {
    const copy = document.createElement("img");                          // a head at its @2x, as `head` (util.js) draws it
    copy.className = "gather-fly";
    copy.src = `races/${race}-${tier}@2x.png`;
    copy.alt = "";
    copy.draggable = false;
    copy.setAttribute("aria-hidden", "true");
    Object.assign(copy.style, { left: `${box.left}px`, top: `${box.top}px`, width: `${box.width}px`, height: `${box.height}px` });
    const vars = { "--dx": `${Math.round(cx - (box.left + box.width / 2))}px`, "--dy": `${Math.round(cy - (box.top + box.height / 2))}px`, "--s": String(GATHER_SCALE), "--delay": `${k * DEAL_STEP_MS}ms` };
    for (const [name, value] of Object.entries(vars)) copy.style.setProperty(name, value);
    copy.addEventListener("animationend", () => copy.remove());
    document.body.append(copy);
    setTimeout(() => copy.remove(), k * DEAL_STEP_MS + DEAL_LEN_MS + 120);        // (should the animation not end: the page was hidden)
  });
  setTimeout(() => pulse(deckOf()), (heads.length - 1) * DEAL_STEP_MS + DEAL_LEN_MS);        // the deck lit once, when the last head has landed
  return heads.length;
}
