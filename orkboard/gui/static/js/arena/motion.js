// Motion says what changed, never decorates (docs/specs/49-one-window.md §11). Each in steps or a short ease-out, none under
// `prefers-reduced-motion`, none on the first read of a goal, none for what changed while the page was hidden. Ticking words and counts
// never move.
//   a task appears      the field did not have it a moment ago: it rises into its place from below, the side of the person (`.is-drawn`, ≤ 0.36 s)
//   the deal           a plan started by a press in the hand (spec 57): its new cards travel from the stop's box to their places instead of rising (`.is-dealt`,
//                       0.30 s in steps, 35 ms apart, six at most; the rest rise); one of the three moments that travel (decisions §76.3)
//   the gather         a new party saved (spec 63): its seats' heads travel as copies from their seats' boxes to the party's deck (`.arena-gather`, goaltabs.js, six at most,
//                       the deal's steps), the deck lit once after; none after Edit the party's save; one of the three
//   the flags raised    the first time the flag line stands for a gate's merge (spec 64, flags.js, partyline.js): its goals' elements (six at most) travel from the merge's press, else the gate's
//                       button, to its row (`.arena-flagfly`, the deal's steps: 0.30 s, 35 ms apart); then its flag steps up 6 px (0.18 s) and the line is lit once (0.6 s);
//                       one of the three
//   a task leaves       merged or dropped: its item fades where it stands with a one-frame ✓ (✗ for a drop), ≈ 0.3 s (`.is-leaving`); then its
//                       column settles: the queue behind it steps up toward the member into the gap (≈ 0.25 s, ease-out). The first three animate, the rest go.
//   a task moves        its state changed its place: it and the items it passes slide to their new places (FLIP: each item's old box measured
//                       before the redraw, its new one after, the difference played back, ≈ 0.25 s); nothing else moves
//   nothing moves under the pointer or the focus: while the pointer is over a column or the focus is inside it, its settle and moves wait
//                       (the gap stays empty) until the pointer leaves or the focus goes, at most 10 s
//   a stop leaves      answered or withdrawn, the stop in the hand fades where it stands (`useLeaving`, spec 58 §4), in the render its task changes; then the hand closes the gap
//   the quiet reward    a merge lights its member's first number and its column's ✓ k in dev once (≈ 0.6 s); nothing flies to them
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { DEAL_KEEP_MS, deal, dropDeal } from "./arenastate.js";

export const FADE_MS = 300, SETTLE_MS = 250, DRAWN_MS = 450, LIT_MS = 600, HOLD_MS = 10000, LEAVING = 3;
export const APART_MS = 35, DEALT = 6, DEALT_MS = 620;      // the gap between two dealt cards, how many travel, when the last one (or the rise after the sixth) has ended
export const GHOST_MS = 300;                                 // a stop's fade in the hand
const SHARE_MS = 400;                                        // how long a taken deal is still read by the other columns of the same render (effects run after the paint) before it is dropped
export const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
/** Motion plays only while the page is seen and the person has not asked for none. */
const plays = () => !reducedMotion() && !(typeof document !== "undefined" && document.hidden);
const held = (el) => !!el && el.matches(":hover, :focus-within");
const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

/** The boxes of every `[data-key]` item of a column, by key. */
function boxes(el) {
  const out = new Map();
  el?.querySelectorAll("[data-key]").forEach((x) => out.set(x.dataset.key, x.getBoundingClientRect()));
  return out;
}

/** Plays the difference between the boxes measured before a redraw and the ones now (FLIP): only what moved moves. */
function play(el, from) {
  el?.querySelectorAll("[data-key]").forEach((x) => {
    const a = from.get(x.dataset.key);
    if (!a || typeof x.animate !== "function") return;
    const b = x.getBoundingClientRect(), dx = a.left - b.left, dy = a.top - b.top;
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;
    x.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: SETTLE_MS, easing: "ease-out" });
  });
}

/** The deal waiting, taken by the first render where its goal's cards are new on the field (spec 57 §1.3): `keys` are the new keys; returns {from, id, keys: the goal's} or null (no deal,
 *  late, motion does not play, no card of its goal). The deal is dropped after SHARE_MS, once this render's other columns have read it (their effects run after the paint). */
function claimDeal(keys) {
  const d = deal.value;
  if (!d || !plays() || Date.now() - d.at > DEAL_KEEP_MS) return null;
  const mine = keys.filter((k) => k.startsWith(`${d.goal}/`));
  if (!mine.length) return null;
  setTimeout(() => dropDeal(d), SHARE_MS);
  return { from: d.from, id: d, keys: mine };
}
let slots = { id: null, n: 0 };                              // the cards of one deal taken so far, over all the columns (the field's order: left column first)
const risen = new Set();                                     // the keys of this deal that rise after the sixth (a redraw keeps them rising, not dealt)
/** Whether a card of the deal rises (it came after the sixth) rather than travels: a card redrawn by itself (a signal) asks it, with the props it had. */
export const rises = (key) => risen.has(key);

/** The dealt cards of a column, just drawn: each from the stop's box (its centre, at the stop's width) to its own box; the first six travel, the rest rise after the sixth starts (spec 57 §2). */
function dealOut(el, view) {
  if (slots.id !== view.id) { slots = { id: view.id, n: 0 }; risen.clear(); }
  const f = view.from, fx = f.left + f.width / 2, fy = f.top + f.height / 2;
  el.querySelectorAll(".arena-task.is-dealt").forEach((card) => {
    if (card.style.getPropertyValue("--dx")) return;         // set already: a redraw of the column during the deal
    const i = slots.n++;
    if (i >= DEALT) { risen.add(card.dataset.key); card.classList.replace("is-dealt", "is-drawn"); card.style.animationDelay = `${DEALT * APART_MS}ms`; return; }
    const r = card.getBoundingClientRect();
    card.style.setProperty("--dx", `${fx - (r.left + r.width / 2)}px`);
    card.style.setProperty("--dy", `${fy - (r.top + r.height / 2)}px`);
    card.style.setProperty("--s", String(Math.round((f.width / r.width) * 1000) / 1000));
    card.style.setProperty("--delay", `${i * APART_MS}ms`);
  });
  if (el.scrollTop === 0) el.classList.add("is-dealing");   // the cards travel over the field: the column does not clip them for a moment
}

/** A column's items as it shows them: `items` now (each with a stable `key(item)`), `signOf(old)` the sign an item that is gone leaves with
 *  (✓ merged, ✗ dropped, "" for one that only went elsewhere). Returns [{it, key, sign, quiet, fresh, dealt}]: `sign` an item fading where it
 *  stood, `quiet` one gone with no fade (past the first three), `fresh` one that rises in, `dealt` one that travels in from the stop of the plan just started
 *  (only when `deals`: the field's columns; a column that is new while the deal waits takes it too). `ref` is the column's element. */
export function useColumn(ref, items, key, signOf, deals = false) {
  const [view, setView] = useState(() => {
    const list = items.map((it) => ({ it, key: key(it), sign: "", quiet: false })), got = deals ? claimDeal(list.map((x) => x.key)) : null;
    return { list, fresh: [], dealt: got ? got.keys : [], from: got?.from, id: got?.id };
  });
  const now = useRef(items);
  now.current = items;
  const me = useRef({ view, busy: false, waiting: false, force: false, hold: 0, timer: 0 });
  me.current.view = view;
  const from = useRef(null);
  const sig = items.map(key).join("|");
  const endDrawn = (ms) => {                                // what rose or was dealt is drawn as it is after `ms`
    const s = me.current;
    clearTimeout(s.timer);
    s.timer = setTimeout(() => { s.timer = 0; ref.current?.classList.remove("is-dealing"); setView((v) => ({ ...v, fresh: [], dealt: [] })); }, ms);
  };

  const settle = () => {                                   // the column takes what the Board says now, and plays what moved
    const s = me.current;
    if (!s.force && held(ref.current)) {                  // under the pointer or the focus: wait, at most HOLD_MS
      if (!s.waiting) { s.waiting = true; s.hold = setTimeout(() => { s.force = true; settle(); }, HOLD_MS); }
      return;
    }
    clearTimeout(s.hold);
    s.waiting = s.force = s.busy = false;
    const next = now.current, had = new Set(s.view.list.map((x) => x.key));
    from.current = plays() ? boxes(ref.current) : null;
    const all = plays() ? next.map(key).filter((k) => !had.has(k)) : [], got = deals && all.length ? claimDeal(all) : null;
    const fresh = got ? all.filter((k) => !got.keys.includes(k)) : all;
    setView({ list: next.map((it) => ({ it, key: key(it), sign: "", quiet: false })), fresh, dealt: got ? got.keys : [], from: got?.from, id: got?.id });
    if (all.length) endDrawn(got ? DEALT_MS : DRAWN_MS);
  };

  useEffect(() => {
    const s = me.current;
    if (s.busy || s.waiting) return;                       // a fade is playing or the column waits: its settle reads what is there then
    const live = s.view.list.filter((x) => !x.sign && !x.quiet).map((x) => x.key), next = items.map(key);
    if (same(live, next)) {                  // nothing moved: only what the items say changes
      if (live.length === s.view.list.length) setView((v) => ({ ...v, list: v.list.map((x) => ({ ...x, it: items.find((i) => key(i) === x.key) || x.it })) }));
      return;
    }
    if (!plays()) { s.waiting = false; s.force = true; settle(); return; }
    const gone = s.view.list.filter((x) => !x.sign && !x.quiet && !next.includes(x.key));
    const fade = gone.map((x) => ({ x, sign: signOf(x.it) })).filter((g) => g.sign).slice(0, LEAVING);
    if (!fade.length) { settle(); return; }
    s.busy = true;                                          // what is gone fades where it stands, then the column settles
    const out = new Map(fade.map((g) => [g.x.key, g.sign]));
    setView((v) => ({ ...v, list: v.list.map((x) => (out.has(x.key) ? { ...x, sign: out.get(x.key) } : gone.includes(x) ? { ...x, quiet: true } : x)) }));
    setTimeout(settle, FADE_MS);
  }, [sig]);

  useLayoutEffect(() => {                                   // the redraw is in: play where things were to where they are
    const was = from.current;
    from.current = null;
    if (was) play(ref.current, was);
    if (view.dealt.length && ref.current) { dealOut(ref.current, view); if (!me.current.timer) endDrawn(DEALT_MS); }
  }, [view]);

  useEffect(() => {                                         // the pointer leaves or the focus goes: what waited is settled
    const el = ref.current;
    if (!el) return undefined;
    const release = () => { if (me.current.waiting) setTimeout(() => { if (!held(el)) settle(); }, 0); };
    el.addEventListener("pointerleave", release);
    el.addEventListener("focusout", release);
    return () => { el.removeEventListener("pointerleave", release); el.removeEventListener("focusout", release); clearTimeout(me.current.hold); clearTimeout(me.current.timer); };
  }, []);

  const latest = new Map(items.map((i) => [key(i), i]));
  return view.list.map((x) => ({ ...x, it: latest.get(x.key) || x.it, fresh: view.fresh.includes(x.key) || (view.dealt.includes(x.key) && risen.has(x.key)), dealt: view.dealt.includes(x.key) && !risen.has(x.key) }));
}

/** A list that does not shift while one of its items is raised (the stops along the bottom): what changes waits until the pointer leaves or
 *  the focus goes, at most HOLD_MS — but not what the raised one lost (it was answered): that goes at once. */
export function useHeld(ref, items, key) {
  const [shown, setShown] = useState(items);
  const now = useRef(items);
  now.current = items;
  const hold = useRef(0);
  const sig = items.map(key).join("|");
  const apply = () => { clearTimeout(hold.current); hold.current = 0; setShown(now.current); };
  useLayoutEffect(() => {                                   // before the paint: a stop that leaves goes in the frame its task changes (spec 58 §4)
    const el = ref.current;
    if (!held(el)) { apply(); return; }
    const raised = [...el.querySelectorAll("[data-key]")].find((x) => x.matches(":hover, :focus-within"));
    if (raised && !items.some((i) => key(i) === raised.dataset.key)) { apply(); return; }
    if (!hold.current) hold.current = setTimeout(apply, HOLD_MS);
  }, [sig]);
  useEffect(() => {
    const el = ref.current;
    const release = () => setTimeout(() => { if (hold.current && !held(el)) apply(); }, 0);
    el?.addEventListener("pointerleave", release);
    el?.addEventListener("focusout", release);
    return () => { el?.removeEventListener("pointerleave", release); el?.removeEventListener("focusout", release); clearTimeout(hold.current); };
  }, []);
  const latest = new Map(items.map((i) => [key(i), i]));
  return shown.map((x) => latest.get(key(x)) || x);
}

/** A stop that leaves the hand (answered, or withdrawn) fades where it stands (spec 58 §4): it stays in the list for GHOST_MS as a ghost (`ghost: true`; `raised` when it was raised,
 *  under the pointer or the focus, so that it fades up there), at the place it had, then the hand closes the gap. It is made in the render that rereads the Board, the one in which its
 *  task changes. None under `prefers-reduced-motion` or while the page is hidden. Returns `items` with the ghosts in. */
export function useLeaving(ref, items, key) {
  const last = useRef({ sig: items.map(key).join("|"), items }), ghosts = useRef([]), [, tick] = useState(0);
  const sig = items.map(key).join("|");
  if (sig !== last.current.sig) {
    const now = new Set(items.map(key));
    ghosts.current = ghosts.current.filter((g) => !now.has(key(g.it)));
    last.current.items.forEach((it, at) => {
      const k = key(it);
      if (now.has(k) || ghosts.current.some((g) => key(g.it) === k) || !plays()) return;
      const el = ref.current?.querySelector(`[data-key="${CSS.escape(k)}"]`);
      ghosts.current.push({ it, at, raised: !!el && el.matches(":hover, :focus-within") });
    });
    last.current = { sig, items };
  }
  useEffect(() => {
    ghosts.current.filter((g) => !g.timer).forEach((g) => {
      g.timer = setTimeout(() => { ghosts.current = ghosts.current.filter((x) => x !== g); tick((n) => n + 1); }, GHOST_MS);
    });
  }, [sig]);
  useEffect(() => () => ghosts.current.forEach((g) => clearTimeout(g.timer)), []);
  const out = items.slice();
  [...ghosts.current].sort((a, b) => a.at - b.at).forEach((g) => out.splice(Math.min(g.at, out.length), 0, { ...g.it, ghost: true, raised: g.raised }));
  return out;
}

/** The quiet reward: `value` changed after the first read — the element lights once (≈ 0.6 s, in steps), then is as it was. */
export function useLit(ref, value) {
  const was = useRef(value);
  useEffect(() => {
    if (was.current !== value && plays() && ref.current && typeof ref.current.animate === "function") {
      ref.current.animate([{ background: "var(--ork-ink)", color: "var(--ork-on-ink)" }, { background: "transparent" }], { duration: LIT_MS, easing: "steps(4, end)" });
    }
    was.current = value;
  }, [value]);
}
