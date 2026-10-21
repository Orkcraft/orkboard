// The gate (docs/specs/49-one-window.md §5.6, §2.1): beside the party row, Merge dev into main and how many goals in dev wait for main, and under the button the quiet
// line *results go into dev* (spec 50 §3.1);
// *main is up to date* (off) when nothing waits; not drawn when dev and main are one branch. A press opens the gate's screen in the
// drawer: the goals listed under *In dev, not in main* with their goals, the commits and files counts, and the one press that merges.
import { html } from "../html.js";
import { Chev, Sign } from "../orkui.js";
import { toast } from "../link.js";
import { act, showGate, gateData, mapData, review } from "../shell/store.js";
import { openDialog } from "../shell/modals.js";
import { gateOf, plural } from "./arenawords.js";

/** *results go into dev ⌄*: the branch the results merge into (spec 50 §3.1); a press opens the same dialog as the results' own *Merge into*. */
function IntoLine() {
  const into = review.value?.into;
  if (!into) return null;
  return html`<button type="button" class="arena-into" aria-haspopup="dialog" title="The branch a result merges into: change it" onClick=${() => openDialog("into")}><span>results go into <b>${into}</b></span><${Chev} /></button>`;
}

export function GateBox() {
  const gate = gateOf(gateData.value);
  if (!gate) return html`<div class="arena-gate is-none"><${IntoLine} /></div>`;
  return html`<div class="arena-gate">
    <div class="arena-gate__row"><button type="button" class="ork-btn primary arena-gate__btn" disabled=${gate.off} onClick=${() => showGate({ via: "gate" })}>${gate.label}</button>
      <span class="arena-cap">${gate.words}</span></div>
    <${IntoLine} />
  </div>`;
}

export function GateView() {
  const gate = gateData.value, shape = gateOf(gate);
  if (!gate || !shape) return html`<p class="ok-tone-muted">${gate ? "Results merge into main itself: there is no gate." : "Reading the gate…"}</p>`;
  const goals = Object.fromEntries((mapData.value?.goals || []).map((g) => [g.slug, g.title]));
  const merge = async () => {
    const got = await act("ideas.gate_merge", {});
    if (got?.note) toast(got.note, "warning");
  };
  return html`<div class="arena-gateview">
    <div class="arena-gateview__head"><span class="shell-ptab__kind">The gate</span><h2>${gate.into} → ${gate.main}</h2>
      <span class="arena-cap">${shape.off ? `${gate.main} has every goal of ${gate.into}` : shape.words}</span></div>
    <section aria-label=${shape.off ? `In ${gate.main}` : `In ${gate.into}, not in ${gate.main}`}>
      <h3 class="board-sub">${shape.off ? `In ${gate.main}` : `In ${gate.into}, not in ${gate.main}`}</h3>
      ${gate.ideas.length ? html`<ul class="arena-done">${gate.ideas.map((i) => html`<li key=${i.slug}><span class="arena-ok"><${Sign} name="check" /></span> ${i.title} <span class="arena-cap">· ${goals[i.goal] || i.goal} · ${plural(i.tasks, "task", "tasks")}</span></li>`)}</ul>`
        : html`<p class="ok-tone-muted">${shape.off ? "Nothing is waiting." : "Nothing of a goal’s: only commits."}</p>`}
      <p class="arena-cap">${plural(gate.commits, "commit", "commits")} · ${plural(gate.files, "file", "files")}</p>
    </section>
    <div class="board-row"><button type="button" class="ork-btn primary" disabled=${shape.off} onClick=${merge}>${shape.label}</button>
      <span class="arena-cap">Nothing reaches ${gate.main} without you.</span></div>
  </div>`;
}
