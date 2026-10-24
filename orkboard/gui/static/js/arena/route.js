// A goal's route on the desktop (docs/specs/68-release-and-route.md §2.1, §7.1): at the top of the goal's screen in the drawer, the steps it took across the parties, oldest first, joined by orkUI's ›,
// each one line — the head of the party's leader (small), then its words: *From Ideation: Invest, 22 Oct* · *Moved from Mobile app* · *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* ·
// *Out in 1.4*. Each step is a button that opens what it names: the pitch's screen, that party with the goal picked into the filter (spec 50 §3.5), or the release goal's screen. A goal with only its
// party step has no route to show: no line. The words are releasewords.js; the host's `route` (`ideas.page`, `ideas.map`) is the data.
import { html, cls } from "../html.js";
import { Chev, Head } from "../orkui.js";
import { track } from "../board/store.js";
import { showIdea } from "../shell/store.js";
import { picks, leaveParty } from "./arenastate.js";
import { partyOf, routeWords } from "./releasewords.js";

/** Where a step leads: the pitch's screen, the release goal's screen, or the step's party with the goal picked into its filter (a party the goal was moved from no longer holds it: shown whole). */
export function openStep(step, goal) {
  if (step.step === "pitch" || step.step === "release") { showIdea(step.goal); return; }
  const party = step.step === "moved" ? step.from || step.party : step.party;
  if (!partyOf(party)) return;
  picks.value = { ...picks.value, [party]: step.step === "moved" ? [] : [goal || step.goal] };
  if (track.value !== party) { leaveParty(); track.value = party; }
}

/** The route's line; nothing when there is none. `steps`: as the host sends them; `goal`: the slug of the goal whose screen this is. */
export function RouteLine({ steps, goal }) {
  if (!Array.isArray(steps) || !steps.length) return null;
  const last = steps.length - 1;
  return html`<nav class="arena-route" aria-label="Route"><h3 class="arena-route__label">Route</h3>
    <div class="arena-route__steps">${steps.map((step, i) => {
      const words = routeWords(step), head = partyOf(step.step === "moved" ? step.from || step.party : step.party)?.leader?.head;
      return html`${i > 0 && html`<${Chev} dir="right" />`}<button type="button" key=${i} class=${cls("arena-route__step", { "is-now": i === last })} data-step=${step.step} title=${words}
        aria-current=${i === last ? "step" : undefined} onClick=${() => openStep(step, goal)}>
        ${head && html`<${Head} race=${head.race} tier=${head.tier} small=${true} />`}<span class="arena-route__words">${words}</span></button>`;
    })}</div></nav>`;
}
