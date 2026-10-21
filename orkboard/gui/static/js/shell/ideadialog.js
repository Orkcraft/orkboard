// New goal (docs/specs/50-parties-and-goals.md §3.3, §3.7; spec 35 §3): the card turned over from the pile — the element the goal will get (`.ork-elem.big`: the
// host's rule over the party's open goals, so it is what `ideas.add` answers), the text, the party (required: the one chosen on the board, else the first by priority;
// General is not listed), the lens of the party (lens.js: what the goal points at, beside its text) and the priority (default the party's). *Add the goal* adds it;
// *Put it back* closes the dialog — closed with text in it, the goal goes to tonight's queue (never lost); closed empty it adds nothing. The code's idea is a goal.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { goalList, track, PRIORITY_WORDS } from "../board/store.js";
import { act, mapData } from "./store.js";
import { Modal, closeDialog } from "./modals.js";
import { Lens, lensValue, noLens, useLenses } from "./lens.js";
import { Elem } from "../orkui.js";
import { nextElement } from "../arena/goalwords.js";

export function IdeaDialog({ goal: first = "" }) {
  const parties = goalList();
  const [text, setText] = useState("");
  const [party, setParty] = useState(first || (parties.some((g) => g.slug === track.value) ? track.value : parties[0]?.slug) || "");
  const [mine, setMine] = useState("");                      // the person's own priority; "" = the party's
  const [busy, setBusy] = useState(false);
  const [lens, setLens] = useState(noLens);
  const info = useLenses(party);
  const priority = mine || parties.find((g) => g.slug === party)?.priority || "normal";
  const element = nextElement((mapData.value?.nodes || []).filter((n) => n.goal === party));
  const send = async () => {
    const t = text.trim();
    if (!t || !party || busy) return;
    setBusy(true);
    const pointed = lensValue(info, lens);
    const got = await act("ideas.add", { text: t, track: party, priority, ...(pointed.length ? { lens: pointed } : {}) });
    setBusy(false);
    if (got?.slug) closeDialog();
  };
  const close = async () => {                 // closed with text in it: tonight's queue
    const t = text.trim();
    closeDialog();
    const pointed = lensValue(info, lens);
    if (t && party) await act("ideas.add", { text: t, track: party, priority, night: true, ...(pointed.length ? { lens: pointed } : {}) });
  };
  return html`<${Modal} title="New goal" onClose=${close} wide=${(info?.lenses || []).length > 1}
    foot=${html`<button type="button" class="ork-btn" onClick=${close}>Put it back</button>
      <button type="button" class="ork-btn primary" disabled=${!text.trim() || !party || busy} onClick=${send}
        title=${say("Add it: the Taskmaster drafts it at once, or tonight when its priority is Low")}>Add the goal</button>`}>
    <div class="shell-form">
      <div class="shell-blank" data-element=${element}><${Elem} name=${element} big=${true} /><b>A blank goal</b></div>
      <label class="shell-field"><span class="ok-font-label">Your goal</span>
        <textarea class="ork-field" rows="4" autofocus value=${text} aria-label="Your goal" placeholder="Your goal, in a few words or a few lines"
          onInput=${(e) => setText(e.target.value)}
          onKeyDown=${(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); send(); } }}></textarea></label>
      <label class="shell-field"><span class="ok-font-label">Belongs to party</span>
        <select class="ork-field" aria-label="Party" value=${party} onChange=${(e) => { setParty(e.target.value); setMine(""); }}>
          ${parties.map((g) => html`<option key=${g.slug} value=${g.slug}>${g.title}</option>`)}</select></label>
      <${Lens} info=${info} s=${lens} set=${setLens} />
      <label class="shell-field"><span class="ok-font-label">Priority</span>
        <select class="ork-field" aria-label="Priority" value=${priority} onChange=${(e) => setMine(e.target.value)}>
          ${Object.entries(PRIORITY_WORDS).map(([id, name]) => html`<option key=${id} value=${id}>${name}</option>`)}</select></label>
      <p class="ok-font-status ok-tone-muted">${say("High and Normal: the Taskmaster drafts it at once. Low: tonight. Closing this with text in it adds it to tonight's queue.")}</p>
    </div>
  <//>`;
}
