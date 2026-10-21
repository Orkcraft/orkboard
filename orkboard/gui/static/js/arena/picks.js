// Pick one's tiles (docs/specs/51-pick-one.md §5, §6): one component per kind of media, the same in the raised stop along the bottom (small, two by two) and in
// the drawer (large, four across at 1 440). A tile is a picture contained on the canvas ground (never cropped, never drawn past twice its size, crisp when it
// is 64 px or less), a clip's first frame with the *film* sign and its length, a sound with the *sound* sign, its length and a thin bar of where it is, or a
// text's words with the *text* sign. Under each tile its label strip (*B · monogram*) is the radio that picks it (`role="radio"`, `aria-checked`): the picked
// one wears a double ink line, and the *check* sign closes its strip. A sound's and a clip's *Play*/*Pause* are a target of their own, apart from the strip: playing never picks.
// Nothing plays by itself (no `autoplay`, `play()` only on a press), a clip's sound is off until the person turns it on, and one plays at a time on the
// whole page (the others pause when one starts). Nothing here animates: the bar only says where the media is.
import { useEffect, useRef, useState } from "preact/hooks";
import { signal } from "@preact/signals";
import { html, cls } from "../html.js";
import { Sign } from "../orkui.js";
import { groupWords, isCapped, isPixel, labelOf, lengthWords, UPSCALE_MAX, variantOf } from "./pickwords.js";

/** What the person has picked and noted, by pick (goal/task/round): the card and the drawer of one pick share it. */
export const choices = signal({});          // "<goal>/<task>/<round>" → {key, note}
const idOf = (row) => `${row.slug}/${row.task}/${row.round || 1}`;
/** The picked variant's key ("" with none) and the note so far. A key the variants no longer have is none. */
export function choiceOf(row) {
  const c = choices.value[idOf(row)] || { key: "", note: "" };
  return variantOf(row, c.key) ? c : { ...c, key: "" };
}
export function choose(row, patch) {
  choices.value = { ...choices.value, [idOf(row)]: { ...choiceOf(row), ...patch } };
}

const MEDIA_SELECTOR = ".pick-tile audio, .pick-tile video";

/** A sound's or a clip's element and what it says now (`on`: playing, `t` and `dur`: where it is, `bad`: it will not play, `sound`: a clip's sound is on). *Play*
 *  starts it and pauses every other one on the page; nothing starts it but a press. */
function useMedia(seconds) {
  const el = useRef();
  const [s, set] = useState({ on: false, t: 0, dur: seconds > 0 ? seconds : 0, bad: false, sound: false });
  const up = (p) => set((x) => ({ ...x, ...p }));
  const toggle = () => {
    const m = el.current;
    if (!m) return;
    if (!m.paused) { m.pause(); return; }
    document.querySelectorAll(MEDIA_SELECTOR).forEach((o) => { if (o !== m && !o.paused) o.pause(); });
    m.play().catch((e) => { if (e?.name !== "AbortError") up({ bad: true, on: false }); });
  };
  const events = {
    onPlay: () => up({ on: true }), onPause: () => up({ on: false }), onEnded: () => up({ on: false, t: 0 }),
    onTimeUpdate: () => up({ t: el.current?.currentTime || 0 }),
    onLoadedMetadata: () => { const d = el.current?.duration; if (Number.isFinite(d) && d > 0) up({ dur: d }); },
    onError: () => up({ bad: true, on: false }),
  };
  return { el, s, toggle, events, sound: () => up({ sound: !s.sound }) };
}

/** A picture, contained on the canvas ground: never cropped, never drawn past twice its size, crisp (`pixelated`) when it is 64 px or less on its side. */
function Picture({ v, label }) {
  const [own, setOwn] = useState({ w: 0, h: 0 }), [bad, setBad] = useState(false);
  const w = v.w || own.w, h = v.h || own.h;
  if (bad) return html`<span class="pick-miss">It will not show</span>`;
  return html`<img class=${cls("pick-img", { "is-capped": isCapped(v.mime, w, h), "is-pixel": isPixel(v.mime, w, h) })} src=${v.url} alt=${label} draggable="false"
    style=${isCapped(v.mime, w, h) ? `width:min(100%,${w * UPSCALE_MAX}px);height:min(100%,${h * UPSCALE_MAX}px)` : undefined}
    onLoad=${(e) => setOwn({ w: e.currentTarget.naturalWidth, h: e.currentTarget.naturalHeight })} onError=${() => setBad(true)} />`;
}

/** A sound or a clip: the media, the sign and its length, *Play* or *Pause* (and a clip's sound), the bar of where it is. */
function Player({ v, label, video, big }) {
  const m = useMedia(v.seconds), { s } = m, len = lengthWords(v.seconds > 0 ? v.seconds : s.dur > 0 ? s.dur : null);
  const word = s.on ? "Pause" : "Play";
  return html`<div class=${cls("pick-player", { "is-video": video, "is-on": s.on })}>
    ${video ? html`<video ref=${m.el} class="pick-video" src=${`${v.url}#t=0.001`} preload="metadata" playsinline muted=${!s.sound} aria-label=${label} ...${m.events}></video>`
      : html`<audio ref=${m.el} src=${v.url} preload="metadata" ...${m.events}></audio>`}
    ${video ? html`<span class="pick-badge"><${Sign} name="film" />${len && html`<span class="pick-len">${len}</span>`}</span>`
      : html`<span class="pick-sound"><${Sign} name="sound" big=${big} />${len && html`<span class="pick-len">${len}</span>`}</span>`}
    ${s.bad ? html`<span class="pick-miss">It will not play here</span>` : html`<span class="pick-ctl">
      <button type="button" class="ork-btn pick-btn pick-play" aria-label=${`${word} ${label}`} title=${word} onClick=${m.toggle}><${Sign} name=${s.on ? "pause" : "play"} /><span class="pick-play__w">${word}</span></button>
      ${video && html`<button type="button" class="ork-btn pick-btn pick-snd" aria-pressed=${s.sound} aria-label=${`${s.sound ? "Turn the sound off" : "Turn the sound on"}: ${label}`}
        title=${s.sound ? "Turn the sound off" : "Turn the sound on"} onClick=${m.sound}><${Sign} name="sound" /></button>`}</span>`}
    <span class="pick-bar" role="progressbar" aria-label=${`Where ${label} is`} aria-valuemin="0" aria-valuemax=${Math.round(s.dur)} aria-valuenow=${Math.round(s.t)}>
      <i style=${`width:${s.dur > 0 ? Math.min(100, (s.t / s.dur) * 100) : 0}%`}></i></span>
  </div>`;
}

/** A text: its words (the first lines in a small tile; the whole text, scrolled, in a large one), the *text* sign before them. */
function Words({ v, label, big }) {
  return html`<div class="pick-words" tabindex=${big ? 0 : undefined} role=${big ? "group" : undefined} aria-label=${big ? label : undefined}>
    <span class="pick-words__sign"><${Sign} name="text" /></span><p class="pick-words__t">${v.text || ""}</p></div>`;
}

function Tile({ row, v, big, on, tab, onPick }) {
  const label = labelOf(v);
  const press = (e) => { if (!e.target.closest("button")) onPick(v.key); };                  // the picture is a target too; *Play* and the sound are not
  return html`<div class=${cls("pick-tile", { "is-on": on })} data-variant=${v.key} data-media=${row.media}>
    <div class="pick-tile__media" onClick=${press}>
      ${row.media === "image" ? html`<${Picture} v=${v} label=${label} />` : row.media === "text" ? html`<${Words} v=${v} label=${label} big=${big} />`
        : html`<${Player} v=${v} label=${label} video=${row.media === "video"} big=${big} />`}
    </div>
    <button type="button" role="radio" aria-checked=${on} class="pick-tile__label" data-variant=${v.key} tabindex=${tab ? 0 : -1} title=${v.why || label}
      onClick=${() => onPick(v.key)}><span class="pick-tile__t">${label}</span>${on && html`<span class="pick-tile__on" aria-hidden="true"><${Sign} name="check" /></span>`}</button>
  </div>`;
}

/** The variants of a pick, a radio group: the card's (small, two by two) or the drawer's (`big`, four across). ← → (and ↑ ↓) move to the next tile and pick it, as
 *  a group of radios does; a keystroke in the note or in a field is not the group's. */
export function Tiles({ row, big = false }) {
  const keys = row.variants.map((v) => v.key), on = choiceOf(row).key;
  const pick = (key) => choose(row, { key });
  const move = (e) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!step || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    const at = keys.indexOf(e.target.closest("[data-variant]")?.dataset.variant);
    if (at < 0) return;
    e.preventDefault();
    const next = keys[(at + step + keys.length) % keys.length];
    pick(next);
    e.currentTarget.querySelector(`[role=radio][data-variant="${next}"]`)?.focus();
  };
  return html`<div class=${cls("pick-tiles", big ? "is-large" : keys.length > 4 ? "is-small is-three" : keys.length === 2 ? "is-small is-one" : "is-small")} role="radiogroup" aria-label=${groupWords(row)} onKeyDown=${move}>
    ${row.variants.map((v, i) => html`<${Tile} key=${`${row.round || 1}/${v.key}`} row=${row} v=${v} big=${big} on=${v.key === on} tab=${v.key === on || (!on && i === 0)} onPick=${pick} />`)}
  </div>`;
}
