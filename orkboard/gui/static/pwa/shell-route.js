// A goal's route on the phone (docs/specs/68-release-and-route.md §2.1, §7.1): under the goal's title on its screen, the steps it took across the parties, oldest first, joined by orkUI's ›, each one line —
// the head of the party's leader (small), then its words: *From Ideation: Invest, 22 Oct* · *Moved from Mobile app* · *At work in Mobile app · 3 of 7* · *In main* · *In Release 1.4* · *Out in 1.4*.
// Each step is a button of 44 px that opens what it names: the pitch's sheet, that party with the goal picked into the filter (spec 50 §3.5), or the release goal's screen. A route longer than the width wraps:
// never a sideways scroll. A goal with only its party step has no route to show: no line. The words are shell-goals-words.js `routeWords`; the host's `node.route` and `ideas.page`'s `route` are the data.
import { h } from "./util.js";
import { whoHead } from "./shell-who.js";
import { partyNameOf, routeWords } from "./shell-goals-words.js";

/** Where a step leads: the pitch's sheet, the release goal's screen, or the step's party with the goal picked into its filter. `core`: the board's frame (st, open, close, pick). */
export function openStep(core, step, goal) {
  if (step.step === "pitch" || step.step === "release") { core.open({ kind: "idea", slug: step.goal }, "route"); return; }
  const party = step.step === "moved" ? step.from || step.party : step.party;
  const picks = step.step === "moved" ? [] : [goal || step.goal];                    // the party a goal was moved from no longer holds it: shown whole
  core.st.picks = { ...(core.st.picks || {}), [party]: picks };
  core.close();
  core.pick(party);
}

/** The route's line (a node, or null when there is nothing to show): `steps` as the host sends them, `goal`: the slug of the goal whose screen this is. */
export function routeLine(core, steps, goal) {
  if (!Array.isArray(steps) || !steps.length) return null;
  const st = core.st, name = (slug) => partyNameOf(st, slug);
  const last = steps.length - 1;
  const kids = steps.flatMap((step, i) => {
    const head = (st.map?.goals || []).find((g) => g.slug === (step.step === "moved" ? step.from || step.party : step.party))?.leader?.head;
    const words = routeWords(step, name);
    const press = h("button", { class: "route__step", type: "button", "data-step": step.step, "aria-label": words, title: words, ...(i === last ? { "aria-current": "step" } : {}),
      onclick: () => openStep(core, step, goal) }, head ? whoHead(head, true) : null, h("span", { class: "route__words" }, words));
    return i ? [h("i", { class: "ork-chev right route__sep", "aria-hidden": "true" }), press] : [press];
  });
  return h("nav", { class: "route", "aria-label": "Route" }, h("h3", { class: "route__label" }, "Route"), h("div", { class: "route__steps" }, ...kids));
}
