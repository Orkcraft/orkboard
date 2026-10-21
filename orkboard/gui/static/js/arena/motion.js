// Motion says what changed, never decorates (docs/specs/49-one-window.md §11). Each in steps or a short ease-out, none under
// `prefers-reduced-motion`, none on the first read of a goal, none for what changed while the page was hidden. Ticking words and counts
// never move.
//   a task appears      the field did not have it a moment ago: it rises into its column (`.is-drawn`, ≤ 0.36 s)
//   a task leaves       merged or dropped: its item fades where it stands with a one-frame ✓ (✗ for a drop), ≈ 0.3 s (`.is-leaving`); then its
//                       column settles: what it held up slides down into the gap (≈ 0.25 s, ease-out). The first three animate, the rest go.
//   a task moves        its state changed its place: it and the items it passes slide to their new places (FLIP: each item's old box measured
//                       before the redraw, its new one after, the difference played back, ≈ 0.25 s); nothing else moves
//   nothing moves under the pointer or the focus: while the pointer is over a column or the focus is inside it, its settle and moves wait
//                       (the gap stays empty) until the pointer leaves or the focus goes, at most 10 s
//   the quiet reward    a merge lights its member's first number and its column's ✓ k in dev once (≈ 0.6 s); nothing flies to them
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";

export const FADE_MS = 300, SETTLE_MS = 250, DRAWN_MS = 450, LIT_MS = 600, HOLD_MS = 10000, LEAVING = 3;
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

/** A column's items as it shows them: `items` now (each with a stable `key(item)`), `signOf(old)` the sign an item that is gone leaves with
 *  (✓ merged, ✗ dropped, "" for one that only went elsewhere). Returns [{it, key, sign, quiet, fresh}]: `sign` an item fading where it
 *  stood, `quiet` one gone with no fade (past the first three), `fresh` one that rises in. `ref` is the column's element. */
export function useColumn(ref, items, key, signOf) {
  const [view, setView] = useState(() => ({ list: items.map((it) => ({ it, key: key(it), sign: "", quiet: false })), fresh: [] }));
  const now = useRef(items);
  now.current = items;
  const me = useRef({ view, busy: false, waiting: false, force: false, hold: 0, timer: 0 });
  me.current.view = view;
  const from = useRef(null);
  const sig = items.map(key).join("|");

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
    const fresh = plays() ? next.map(key).filter((k) => !had.has(k)) : [];
    setView({ list: next.map((it) => ({ it, key: key(it), sign: "", quiet: false })), fresh });
    if (fresh.length) { clearTimeout(s.timer); s.timer = setTimeout(() => setView((v) => ({ ...v, fresh: [] })), DRAWN_MS); }
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
  return view.list.map((x) => ({ ...x, it: latest.get(x.key) || x.it, fresh: view.fresh.includes(x.key) }));
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
  useEffect(() => {
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
