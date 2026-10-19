// New goal / Edit goal (docs/specs/35-goals-window.md §2): a description and a priority; the Taskmaster writes the rest. Edit
// adds the Title, to correct the Taskmaster's. Saving sends the goal to the Taskmaster at once. A new goal is the three steps of
// goalwizard.js: its craft, its team from the library, what it is for.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { board, track } from "../board/store.js";
import { act, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { GoalWizard } from "./goalwizard.js";

export const PRIORITIES = [["high", "High"], ["normal", "Normal"], ["low", "Low"]];

export function GoalDialog({ slug = "", then = "" }) {
  return slug ? html`<${GoalEdit} slug=${slug} then=${then} />` : html`<${GoalWizard} then=${then} />`;
}

function GoalEdit({ slug, then = "" }) {
  const g = slug ? board.value?.tracks.find((t) => t.slug === slug) : null;
  const [title, setTitle] = useState(g?.title || "");
  const [about, setAbout] = useState(g?.about || "");
  const [priority, setPriority] = useState(g?.priority || "normal");
  const [saving, setSaving] = useState(false);
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const args = { ...(slug ? { slug } : {}), about: about.trim(), priority };
    if (slug && title.trim() && title.trim() !== g?.title) args.title = title.trim();     // a title typed is the person's
    const got = await act("ideas.goal_save", args);
    setSaving(false);
    if (!got?.slug) return;
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };
  return html`<${Modal} title=${slug ? "Edit goal" : "New goal"} onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save goal</button>`}>
    <form id="goal-form" class="shell-form" onSubmit=${save}>
      ${slug && html`<label class="shell-field"><span class="ok-font-label">Title</span>
        <input class="ork-field" value=${title} aria-label="Title" placeholder="The Taskmaster wrote it; correct it here" onInput=${(e) => setTitle(e.target.value)} /></label>`}
      <label class="shell-field"><span class="ok-font-label">Description</span>
        <textarea class="ork-field" rows="5" autofocus value=${about} aria-label="Description" placeholder="A few lines: what you want to reach, and why"
          onInput=${(e) => setAbout(e.target.value)}></textarea></label>
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say("The Taskmaster reads the repository and writes the title, the summary, the metrics and the links.")}</p>
    </form>
  <//>`;
}
