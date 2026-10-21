// The party line (docs/specs/50-parties-and-goals.md §3.2, §3.8): under the tabs, one quiet line of 36 px — *Now: <member> <work> <task> (<goal>) · …*,
// then *≈$2–4 a goal · today 3 merged · ≈$1.10*, *About this party* and *Edit the party*. Nothing else, nothing in the alert colour. After a gate's
// merge that raised flags, the flag line stands under it until it is closed (flags.js): in the success colour, never over the work.
import { html } from "../html.js";
import { Icon, Sign } from "../orkui.js";
import { aboutAt, showGoal } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { usePartyPrice } from "../shell/party.js";
import { todayWords } from "../board/mapstage.js";
import { nowParts, nowWords } from "./arenawords.js";
import { inMainWords, priceWords, raisedWords } from "./goalwords.js";
import { closeFlagLine, flagLine } from "./flags.js";

/** *Backend <work> Credential table (WebAuthn register)* for every member at work, the leader reading, else *nothing at work right now*. */
function Now({ parts }) {
  if (!parts.length) return html`nothing at work right now`;
  return parts.map((b, i) => html`${i > 0 ? " · " : ""}${b.reading ? html`${b.who} <${Sign} name="work" /> reading “${b.reading}”` : html`${b.who} <${Sign} name="work" /> ${b.task} (${b.goal})`}`);
}

export function PartyLine({ g, nodes, lead, reading }) {
  const parts = nowParts(nodes, lead, reading), words = nowWords(parts);
  const seats = g.team || [], price = usePartyPrice(true, g.leader?.slug || "taskmaster", seats.map((m) => m.slug), seats.filter((m) => m.every).map((m) => m.slug), g.craft || "");
  return html`<div class="arena-ibar__bar">
    <span class="arena-ibar__now" title=${words} aria-label=${`Now: ${words}`}><span class="arena-muted">Now:</span> <${Now} parts=${parts} /></span>
    <span class="arena-ibar__goal" title="About what a goal costs with this party, and what was merged today">${[priceWords(price), todayWords(g.today)].filter(Boolean).join(" · ")}</span>
    <button type="button" class="ork-btn quiet" title="What it is for, its party, its checks, its price and its flags" onClick=${() => { aboutAt.value = ""; showGoal(g.slug, { via: "map" }); }}>About this party</button>
    <button type="button" class="ork-btn quiet" onClick=${() => openDialog("goal", { slug: g.slug })}>Edit the party</button>
  </div>`;
}

/** The flag line: *<flag> n flags raised · <a>, <b> and k more are in main* and a close; a press on the words opens About this party at Its flags. */
export function FlagLine() {
  const f = flagLine.value;
  if (!f) return null;
  const open = () => { aboutAt.value = "flags"; showGoal(f.party, { via: "flags" }); };
  return html`<div class="arena-flagline" role="status">
    <button type="button" class="arena-flagline__main" title="Its flags, in About this party" onClick=${open}>
      <span class="arena-flagline__flag"><${Sign} name="flag" /></span><b>${raisedWords(f.n)}</b><span class="arena-flagline__words"> · ${inMainWords(f.shorts)}</span></button>
    <button type="button" class="ork-btn quiet arena-flagline__x" aria-label="Close" title="Close" onClick=${closeFlagLine}><${Icon} name="close" /></button>
  </div>`;
}
