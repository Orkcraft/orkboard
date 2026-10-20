// New goal / Edit goal (docs/specs/35-goals-window.md §2): a description and a priority; the goal's leader writes the rest. Edit
// adds the Title, to correct the leader's, and the Party: Change it opens its three bands (party.js) and its checks; a party
// changed is sent with the goal. Saving sends the goal to its leader at once. A new goal is the three steps of goalwizard.js: its
// craft, its party from the library, what it is for.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say } from "../link.js";
import { board, track } from "../board/store.js";
import { act, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { GoalWizard } from "./goalwizard.js";
import { PartyBands, PriceLine, ChecksBlock, TASKMASTER, partyWords, usePartyPrice } from "./party.js";

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
  const was = { leader: g?.leader?.slug || TASKMASTER, team: g?.team || [], every: g?.every || [] };
  const [leader, setLeader] = useState(was.leader);
  const [team, setTeam] = useState(was.team);
  const [every, setEvery] = useState(was.every);
  const [changing, setChanging] = useState(false);
  const price = usePartyPrice(changing, leader, team, every, g?.craft || "");          // asked when the party is picked (Change the party)
  const moved = leader !== was.leader || JSON.stringify(team) !== JSON.stringify(was.team) || JSON.stringify(every) !== JSON.stringify(was.every);
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const args = { ...(slug ? { slug } : {}), about: about.trim(), priority };
    if (slug && title.trim() && title.trim() !== g?.title) args.title = title.trim();     // a title typed is the person's
    if (moved) Object.assign(args, { leader, team, every: every.filter((id) => team.includes(id)) });   // the party, when changed
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
      <p class="ok-font-status ok-tone-muted">${say(`${g?.leader?.slug && g.leader.slug !== TASKMASTER ? g.leader.name : "The Taskmaster"} reads the repository and writes the title, the summary, the metrics and the links.`)}</p>
      ${g && html`<div class="shell-field" role="group" aria-label="Party"><span class="ok-font-label">Party</span>
        <p class="ok-tone-muted shell-party-line">${partyWords(leader, team)}</p>
        ${changing ? html`<${PartyBands} craft=${g.craft} leader=${leader} setLeader=${setLeader} team=${team} setTeam=${setTeam} />
          <${PriceLine} price=${price} />
          <${ChecksBlock} team=${team} every=${every} setEvery=${setEvery} price=${price} />`
          : html`<button type="button" class="ork-btn" onClick=${() => setChanging(true)}>Change the party</button>`}</div>`}
    </form>
  <//>`;
}
