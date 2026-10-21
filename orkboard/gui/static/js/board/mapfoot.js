// The Map's flags and its foot (docs/specs/42-coming-back.md §2.3–§2.4): a goal's flag is raised once on this device, while it is on
// screen; *Flags (n)* lists the goals met with their tally and what their party did; *Last week*. Split from map.js (spec 48).
import { useEffect, useState } from "preact/hooks";
import { html } from "../html.js";
import { Icon } from "../orkui.js";
import { ask } from "./store.js";
import { mapFolded, lookKey, logOpened, showGoal } from "../shell/store.js";
import { showWeek } from "../shell/look.js";
import { PartyWork } from "../shell/goalview.js";
import { tallyWords, flagWords } from "./maplayout.js";

/** The flags this device raised (spec 42 §2.3): the goals' slugs under `orkboard.flags.<12 characters>`; null on a device with no list. */
const flagsKey = () => lookKey().replace("orkboard.look.", "orkboard.flags.");
function raisedList(key) {
  try {
    const got = JSON.parse(localStorage.getItem(key) || "null");
    return Array.isArray(got) ? got.filter((x) => typeof x === "string") : null;
  } catch { return null; }
}
function keepRaised(key, slugs) {
  try { localStorage.setItem(key, JSON.stringify([...new Set([...(raisedList(key) || []), ...slugs])])); } catch { /* the flag is raised again next time */ }
}
const reducedMotion = () => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

/** A device with no list adds every met goal without raising any (the first start after this part). */
export function seedRaised(m) {
  const key = flagsKey();
  if (key && raisedList(key) === null) keepRaised(key, m.goals.filter((g) => g.verdict?.met).map((g) => g.slug));
}

/** The goal's flag is raised once on this device, while its trail is on screen (the Map shown, the goal unfolded, the page visible):
 *  it moves up from the foot of its box in six steps (not under reduced motion), the slug is kept and `opened` `flag` is logged. */
export function useRaise(g, ref) {
  const [raising, setRaising] = useState(false);
  const met = g.verdict?.met === true;
  useEffect(() => {
    const key = flagsKey();
    const list = key && met ? raisedList(key) : null;
    if (!list || list.includes(g.slug) || !ref.current) return undefined;
    let io, timer, done = false, inView = false;          // whether the observer last saw the trail on screen
    const raise = () => {
      if (done || !inView || document.visibilityState !== "visible") return;
      done = true;
      io?.disconnect();
      keepRaised(key, [g.slug]);
      logOpened("flag", g.slug);
      if (!reducedMotion()) { setRaising(true); timer = setTimeout(() => setRaising(false), 700); }
    };
    if (typeof IntersectionObserver === "function") {
      io = new IntersectionObserver((seen) => { inView = seen[seen.length - 1].isIntersecting; raise(); });
      io.observe(ref.current);
    } else { inView = true; raise(); }
    document.addEventListener("visibilitychange", raise);
    return () => { done = true; io?.disconnect(); clearTimeout(timer); document.removeEventListener("visibilitychange", raise); };
  }, [met, g.slug]);
  return raising;
}

const FLAGS_OPEN = "@flags:open";                                   // in the folds kept with the tabs: the Flags fold is closed until it is opened

/** The foot of the Map (spec 42 §2.4): *Flags (3)*, the goals met, with their tally; the list is asked for when the fold is opened. */
export function MapFoot({ m }) {
  const met = m.goals.filter((g) => g.verdict?.met).length;
  const open = mapFolded.value.includes(FLAGS_OPEN);
  const [flags, setFlags] = useState(null);
  useEffect(() => {
    if (!open || !met) return undefined;
    let on = true;
    ask("ideas.flags").then((got) => { if (on && got) setFlags(got.flags || []); });
    return () => { on = false; };
  }, [open, met, m.rev]);
  const fold = () => { mapFolded.value = open ? mapFolded.value.filter((x) => x !== FLAGS_OPEN) : [...mapFolded.value, FLAGS_OPEN]; };
  return html`<div class="map-foot">
    ${met > 0 && html`<section class="map-flags" aria-label="Flags">
      <button type="button" class="board-link map-flags__btn" aria-expanded=${open} onClick=${fold}>Flags (${met})</button>
      ${open && html`<ul class="map-flags__list">${(flags || []).map((f) => html`<li key=${f.goal}>
        <button type="button" class="map-flag" onClick=${() => showGoal(f.goal, { via: "flags" })}>
          <span class="map-flag__mark" aria-hidden="true"><${Icon} name="flag" /></span>
          <span class="map-flag__body"><b>${f.title}</b><span class="ok-font-status ok-tone-muted">${flagWords(f)}</span>
            <span class="ok-font-status ok-tone-muted">${tallyWords(f.tally)}</span></span></button>
        <${PartyWork} goal=${f.goal} /></li>`)}</ul>`}
    </section>`}
    <button type="button" class="board-link map-foot__week" onClick=${showWeek}>Last week</button>
  </div>`;
}

