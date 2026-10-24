// The party line (docs/specs/50-parties-and-goals.md §3.2, §3.8): under the tabs, one quiet line of 36 px — *Now: <member> <work> <task> (<goal>) · …*,
// then *≈$2–4 a goal · today 3 merged · ≈$1.10*, *About this party* and *Edit the party*. Nothing else, nothing in the alert colour. After a gate's
// merge that raised flags, the flag line stands under it until it is closed (flags.js): in the success colour, never over the work. The first time it stands, its goals'
// elements travel to it from the gate and stay in a row after its flag, then its flag is raised and the line lit once (docs/specs/64-flags-raised.md).
import { useEffect, useLayoutEffect, useRef } from "preact/hooks";
import { html } from "../html.js";
import { Elem, Icon, Sign } from "../orkui.js";
import { aboutAt, showGoal } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { usePartyPrice } from "../shell/party.js";
import { todayWords } from "../board/mapstage.js";
import { nowParts, nowWords } from "./arenawords.js";
import { inMainWords, priceWords, raisedWords } from "./goalwords.js";
import { APART_MS, LIT_MS, reducedMotion } from "./motion.js";
import { closeFlagLine, dropRaise, flagLine, gateButton, raise } from "./flags.js";

/** *Backend <work> Credential table (WebAuthn register)* for every member at work, the leader reading, else *nothing at work right now*. */
function Now({ parts }) {
  if (!parts.length) return html`nothing at work right now`;
  return parts.map((b, i) => html`${i > 0 ? " · " : ""}${b.reading ? html`${b.who} <${Sign} name="work" /> ${b.doing || "reading"} “${b.reading}”` : html`${b.who} <${Sign} name="work" /> ${b.task} (${b.goal})`}`);
}

export function PartyLine({ g, nodes, lead, reading, doing = "reading" }) {
  const parts = nowParts(nodes, lead, reading, doing), words = nowWords(parts);
  const seats = g.team || [], price = usePartyPrice(true, g.leader?.slug || "taskmaster", seats.map((m) => m.slug), seats.filter((m) => m.every).map((m) => m.slug), g.craft || "");
  return html`<div class="arena-ibar__bar">
    <span class="arena-ibar__now" title=${words} aria-label=${`Now: ${words}`}><span class="arena-muted">Now:</span> <${Now} parts=${parts} /></span>
    <span class="arena-ibar__goal" title="About what a goal costs with this party, and what was merged today">${[priceWords(price), todayWords(g.today)].filter(Boolean).join(" · ")}</span>
    <button type="button" class="ork-btn quiet" title="What it is for, its party, its checks, its price and its flags" onClick=${() => { aboutAt.value = ""; showGoal(g.slug, { via: "map" }); }}>About this party</button>
    <button type="button" class="ork-btn quiet" onClick=${() => openDialog("goal", { slug: g.slug })}>Edit the party</button>
  </div>`;
}

const FLY_MS = 300, UP_MS = 180;                    // an element's travel (spec 57's deal), the flag's step up
const plays = () => !reducedMotion() && !document.hidden;

/** The flags raised (spec 64 §2): the elements of the goals waiting travel from `from` (its centre, at its height) to their places in the line's row, as copies over everything,
 *  35 ms apart, 0.30 s in steps; a place stays empty until its copy lands. The line's flag stands 6 px lower until the last lands (at once with nowhere to travel from), then steps up
 *  and the line is lit once (the CSS: `.is-raising` with `--delay`, the end of the travel). Returns what puts it all away (the copies, the classes). */
function raiseFlags(line, goals, from) {
  const slots = [...line.querySelectorAll(".arena-flagline__el")].filter((s) => goals.some((g) => g.slug === s.dataset.slug));
  const fx = from ? from.left + from.width / 2 : 0, fy = from ? from.top + from.height / 2 : 0;
  const copies = !from ? [] : slots.map((slot, i) => {
    const r = slot.getBoundingClientRect(), copy = slot.firstElementChild.cloneNode(true);
    copy.classList.add("arena-flagfly");
    copy.style.left = `${r.left}px`;
    copy.style.top = `${r.top}px`;
    copy.style.setProperty("--dx", `${fx - (r.left + r.width / 2)}px`);
    copy.style.setProperty("--dy", `${fy - (r.top + r.height / 2)}px`);
    copy.style.setProperty("--s", String(Math.round((from.height / r.height) * 1000) / 1000));
    copy.style.setProperty("--delay", `${i * APART_MS}ms`);
    copy.addEventListener("animationend", () => copy.remove(), { once: true });
    slot.classList.add("is-coming");
    slot.style.animationDelay = `${i * APART_MS + FLY_MS}ms`;
    document.body.append(copy);
    return copy;
  });
  const lands = copies.length ? (copies.length - 1) * APART_MS + FLY_MS : 0;
  line.style.setProperty("--delay", `${lands}ms`);
  line.classList.add("is-raising");
  const end = () => {
    clearTimeout(timer);
    copies.forEach((c) => c.remove());
    slots.forEach((s) => { s.classList.remove("is-coming"); s.style.animationDelay = ""; });
    line.classList.remove("is-raising");
    line.style.removeProperty("--delay");
  };
  const timer = setTimeout(end, lands + Math.max(UP_MS, LIT_MS) + 60);
  return end;
}

/** The flag line: *<flag> <elements> n flags raised · <a>, <b> and k more are in main* and a close; a press on the words opens About this party at Its flags. The elements are the line's
 *  first six goals' (each its goal's element, still). The raise waiting is taken in the render that draws them, before it is painted: none under reduced motion or on a hidden page. */
export function FlagLine() {
  const f = flagLine.value, wait = raise.value, line = useRef(), away = useRef(null);
  useLayoutEffect(() => {
    if (!f) { away.current?.(); away.current = null; return; }         // the line is closed: what flies to it goes
    if (!wait || !line.current) return;
    dropRaise(wait);
    if (!plays()) return;
    away.current?.();
    away.current = raiseFlags(line.current, wait.goals, wait.from || gateButton());
  }, [wait, f]);
  useEffect(() => () => away.current?.(), []);
  if (!f) return null;
  const open = () => { aboutAt.value = "flags"; showGoal(f.party, { via: "flags" }); };
  return html`<div class="arena-flagline" role="status" ref=${line}>
    <button type="button" class="arena-flagline__main" title="Its flags, in About this party" onClick=${open}>
      <span class="arena-flagline__flag"><${Sign} name="flag" /></span>
      <span class="arena-flagline__row">${(f.row || []).map((x) => html`<span key=${x.slug} class="arena-flagline__el" data-slug=${x.slug}><${Elem} name=${x.element} /></span>`)}</span>
      <b>${raisedWords(f.n)}</b><span class="arena-flagline__words"> · ${inMainWords(f.shorts)}</span></button>
    <button type="button" class="ork-btn quiet arena-flagline__x" aria-label="Close" title="Close" onClick=${closeFlagLine}><${Icon} name="close" /></button>
  </div>`;
}
