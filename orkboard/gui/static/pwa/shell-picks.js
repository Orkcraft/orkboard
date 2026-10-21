// Pick one on the phone, the tiles (docs/specs/51-pick-one.md §5, §7): one tile to a variant, one component to a kind, drawn the same on the raised stop (2 × 2) and on the
// pick's own screen (one to a screen, swiped with a snap).
//   a picture   contained on the canvas ground, never cropped, never scaled up past 2× (a vector fills its tile), `image-rendering: pixelated` only when it is 64 px or less on its side;
//   a clip      its first frame (`<video preload="metadata" playsinline muted>`), the `film` sign and its length in a corner, *Play* in the tile, its sound off until it is turned on;
//   a sound     the `sound` sign, its length, *Play* / *Pause*, a thin bar of where it is (dragged to seek);
//   a text      its words (the `text` sign): the first lines in the tile, all of them on the pick's own screen.
// Each tile has its label strip under it (*B · monogram*), a radio of the group (`aria-checked`) that **picks** it; a tap on the picture picks it too, but *Play*, the bar and the sound
// switch are targets of their own and never pick. One plays at a time, and nothing plays by itself. A tile is only nodes: what is picked is the caller's (shell-pick-answer.js).
import { h } from "./util.js";
import { sign } from "./shell-marks.js";

const MEDIA = { image: ["picture", "pictures"], audio: ["sound", "sounds"], video: ["clip", "clips"], text: ["text", "texts"] };
const SMALL_SIDE = 64;                               // a picture this small on its side is pixel art: drawn crisp
const UP_TO = 2;                                     // and never drawn larger than this many times its own size

/** *4 pictures*, *3 sounds*: the kind's word (spec 51 §0). */
export const countWords = (n, media) => `${n} ${(MEDIA[media] || MEDIA.image)[n === 1 ? 0 : 1]}`;
/** *B · monogram*: a variant's label. */
export const labelOf = (v) => `${v.key} · ${v.name}`;
/** *0:07*: a length in seconds ("" when it is not known). */
export const lengthWords = (s) => (Number.isFinite(s) && s > 0 ? `${Math.floor(Math.max(1, Math.round(s)) / 60)}:${String(Math.max(1, Math.round(s)) % 60).padStart(2, "0")}` : "");

/** The pick of a task as Needs you says it (`kind: "pick"`), or null when it does not wait any more. */
export const pickRow = (st, slug, task) => (st.board?.needs_you || []).find((n) => n.kind === "pick" && n.slug === slug && n.task === task) || null;
/** What a redraw compares: what the pick shows, not when it was asked (a redraw would stop a sound that is playing). */
export const pickSig = (n) => [n.slug, n.task, n.round, n.title, n.ask, n.media, n.by?.name, (n.variants || []).map((v) => [v.key, v.name, v.url, v.text ?? null])];

// -- one at a time -------------------------------------------------------------------------------------------------------------------------------------
const live = new Set();                              // the media playing now

/** Whether something is playing. */
export const isPlaying = () => live.size > 0;
/** Pauses whatever plays: a card put back, a screen left, new tiles drawn (a detached element goes on playing). */
export function stopAll() { for (const m of [...live]) m.pause(); }
function watch(m) {
  m.addEventListener("play", () => { for (const o of [...live]) if (o !== m) o.pause(); live.add(m); });      // one plays at a time
  for (const type of ["pause", "ended", "emptied", "error"]) m.addEventListener(type, () => live.delete(m));
}

// -- the kinds -----------------------------------------------------------------------------------------------------------------------------------------------
function imageView(v, label) {
  const img = h("img", { class: "pk__img", src: v.url, alt: label, draggable: "false" });
  const vector = /svg/.test(v.mime || "");
  const fit = (w, hh) => {
    if (vector || !(w > 0 && hh > 0)) return;
    img.style.width = `${w * UP_TO}px`;                // the box is at most twice the picture, and `max-width/height: 100%` keeps it in the tile; `object-fit: contain` never crops
    img.style.height = `${hh * UP_TO}px`;
    img.classList.toggle("is-pixel", Math.max(w, hh) <= SMALL_SIDE);
  };
  fit(v.w, v.h);
  if (!vector && !(v.w > 0 && v.h > 0)) img.addEventListener("load", () => fit(img.naturalWidth, img.naturalHeight));      // a size the host could not read: the browser's
  return [img];
}

function textView(v) {
  return [h("span", { class: "pk__sign" }, sign("text")), h("p", { class: "pk__words" }, v.text ?? "")];
}

/** A clip or a sound: the element (a clip's is its picture, a sound's is not drawn), its length, and the controls: *Play* / *Pause*, the bar, and a clip's sound switch. */
function mediaView(media, v, label) {
  const video = media === "video";
  const m = h(media, { class: "pk__media", src: v.url, preload: "metadata", ...(video ? { playsinline: true, muted: true } : { hidden: true }) });
  if (video) m.muted = true;                         // the attribute alone does not mute an element made by script
  watch(m);
  const length = h("span", { class: "pk__len" }, lengthWords(v.seconds));
  const meta = h("span", { class: "pk__meta" }, sign(video ? "film" : "sound", "", { big: !video }), length);
  const flag = sign("play"), word = h("span", { class: "pk__word" }, "Play");
  const play = h("button", { class: "ork-btn pk__play", type: "button" }, flag, word);
  const bar = h("input", { class: "pk__bar", type: "range", min: "0", max: "1000", step: "1", value: "0", "aria-label": `Position of ${label}`, disabled: !(v.seconds > 0) });
  const ctl = h("div", { class: "pk__ctl" }, play, bar);
  let scrubbing = false;
  const show = (on) => { flag.className = `ork-sign ${on ? "pause" : "play"}`; word.textContent = on ? "Pause" : "Play"; play.classList.toggle("is-on", on); };
  const where = (at) => {                            // the thin bar: the part played in ink, the rest in the frame's line
    bar.value = String(Math.round(at * 1000));
    bar.style.background = `linear-gradient(var(--ork-ink) 0 0) 0 50% / ${(at * 100).toFixed(1)}% 4px no-repeat, linear-gradient(var(--ork-frame) 0 0) 0 50% / 100% 4px no-repeat`;
  };
  where(0);
  play.addEventListener("click", () => { if (m.paused) m.play().catch(() => { play.disabled = true; play.title = "This file cannot be played here"; }); else m.pause(); });
  m.addEventListener("play", () => show(true));
  m.addEventListener("pause", () => show(false));
  m.addEventListener("ended", () => { m.currentTime = 0; show(false); where(0); });
  m.addEventListener("loadedmetadata", () => {
    if (Number.isFinite(m.duration) && m.duration > 0) { length.textContent = lengthWords(m.duration); bar.disabled = false; }
    if (video && m.paused && !m.currentTime) m.currentTime = 0.001;               // a first frame to show (a browser may not paint one by itself)
  });
  m.addEventListener("timeupdate", () => { if (!scrubbing && m.duration > 0) where(m.currentTime / m.duration); });
  bar.addEventListener("input", () => { if (m.duration > 0) { m.currentTime = (bar.value / 1000) * m.duration; where(bar.value / 1000); } });
  bar.addEventListener("pointerdown", () => { scrubbing = true; });
  for (const type of ["pointerup", "pointercancel", "change", "blur"]) bar.addEventListener(type, () => { scrubbing = false; });
  if (video) {
    const snd = h("button", { class: "ork-btn pk__snd", type: "button", "aria-pressed": "false", title: "The sound is off: tap to turn it on" }, sign("sound"), h("span", { class: "pk__word" }, "Sound"));
    snd.addEventListener("click", () => {
      m.muted = !m.muted;
      snd.setAttribute("aria-pressed", String(!m.muted));
      snd.title = m.muted ? "The sound is off: tap to turn it on" : "The sound is on: tap to turn it off";
    });
    ctl.append(snd);
  }
  return [m, meta, ctl];
}

// -- a tile ----------------------------------------------------------------------------------------------------------------------------------------------------
/** One variant's tile: the picture (or frame, or sound, or words) over its label strip. `pick(key)` is called by the strip and by a tap on the picture. */
function tile(row, v, { large, pick }) {
  const media = row.media || String(v.mime || "").split("/")[0];
  const label = labelOf(v);
  const view = h("div", { class: "pk__view" }, ...(media === "image" ? imageView(v, label) : media === "text" ? textView(v) : mediaView(media, v, label)),
    h("span", { class: "pk__on", "aria-hidden": "true" }, sign("check")));
  const strip = h("button", { class: "pk__label", type: "button", role: "radio", "aria-checked": "false", "data-key": v.key, tabindex: "-1", title: v.why || null }, label);
  const el = h("div", { class: `pk${large ? " is-large" : ""}`, role: "group", "aria-label": label, "data-key": v.key, "data-kind": media }, view, strip,
    large && v.why ? h("span", { class: "pk__why" }, v.why) : null);
  strip.addEventListener("click", () => pick(v.key));
  view.addEventListener("click", (e) => { if (!e.target.closest(".pk__ctl")) pick(v.key); });     // *Play*, the bar and the sound switch are targets of their own: they never pick
  return { el, strip, key: v.key };
}

/** The tiles of a pick as one radio group. `picked`: the letter picked (or ""), `large`: the tiles of a screen (all the words of a text, the artist's line), `swipe`: one to a screen, sideways
 *  with a snap (the pick's own screen), else 2 × 2; `onPick(key)` when the person picks. Returns {el, pips, key(), choose(key), reveal()}: `pips`: the swipe's dots (null otherwise),
 *  `reveal`: puts the picked tile (else the first) in view once the group is in the page. */
export function tiles(row, { picked = "", large = false, swipe = false, onPick = () => {} } = {}) {
  let key = (row.variants || []).some((v) => v.key === picked) ? picked : "";
  const nodes = (row.variants || []).map((v) => tile(row, v, { large, pick: (k) => choose(k) }));
  const el = h("div", { class: `pks${swipe ? " is-swipe" : ""}`, role: "radiogroup", "aria-label": countWords(nodes.length, row.media) }, ...nodes.map((n) => n.el));
  function mark() {
    nodes.forEach((n, i) => {
      const on = n.key === key;
      n.el.classList.toggle("is-on", on);
      n.strip.setAttribute("aria-checked", String(on));
      n.strip.tabIndex = on || (!key && i === 0) ? 0 : -1;                        // one stop of the Tab: the picked one's (else the first's); the arrows move
    });
  }
  function choose(k, focus = false) {
    if (!nodes.some((n) => n.key === k)) return;
    key = k;
    mark();
    onPick(k);
    if (focus) nodes.find((n) => n.key === k).strip.focus();
  }
  el.addEventListener("keydown", (e) => {
    const at = nodes.findIndex((n) => n.strip === document.activeElement);
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (at < 0 || !step) return;
    e.preventDefault();
    choose(nodes[(at + step + nodes.length) % nodes.length].key, true);
  });
  mark();
  let pips = null;
  if (swipe) {
    pips = h("span", { class: "ork-pips pk-pips", "aria-hidden": "true" }, ...nodes.map(() => h("i")));
    const pitch = () => (nodes[1] ? nodes[1].el.offsetLeft - nodes[0].el.offsetLeft : el.clientWidth) || 1;
    const lit = () => [...pips.children].forEach((p, i) => p.classList.toggle("d", i === Math.round(el.scrollLeft / pitch())));
    let frame = 0;
    el.addEventListener("scroll", () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(lit); }, { passive: true });
    lit();
  }
  return {
    el, pips, key: () => key, choose,
    reveal() {
      if (!swipe) return;
      const at = Math.max(0, nodes.findIndex((n) => n.key === key));
      el.scrollLeft = nodes[at] ? nodes[at].el.offsetLeft - nodes[0].el.offsetLeft : 0;
      [...pips.children].forEach((p, i) => p.classList.toggle("d", i === at));
    },
  };
}

/** The small tiles of the stop's card in the fan: a picture of each (a sign for a clip, a sound, a text), a few pixels each. */
export function thumbs(row) {
  return h("span", { class: "hc__thumbs", "aria-hidden": "true" }, ...(row.variants || []).slice(0, 6).map((v) => {
    const media = row.media || String(v.mime || "").split("/")[0];
    if (media !== "image") return h("span", { class: "hc__thumb" }, sign(media === "video" ? "film" : media === "audio" ? "sound" : "text"));
    const small = !/svg/.test(v.mime || "") && Math.max(v.w || 0, v.h || 0) > 0 && Math.max(v.w, v.h) <= SMALL_SIDE;       // a vector is never pixel art
    return h("span", { class: "hc__thumb" }, h("img", { class: small ? "is-pixel" : "", src: v.url, alt: "", draggable: "false" }));
  }));
}
