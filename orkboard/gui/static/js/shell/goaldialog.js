// Edit the party (docs/specs/50-parties-and-goals.md §3.7): the same fields as New party (goalwizard.js) — its name, *What it is for*, the party, the checks on every
// goal, its priority — on a party that is there: its name is the person's to correct, the party is changed with *Change the party* (its three bands, what it costs a
// goal and its checks, party.js) and sent with it. Saving sends the party to its leader at once. A new party is goalwizard.js's one screen. The code's goal is a party.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { board, track } from "../board/store.js";
import { act, mapData, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { GoalWizard, FOR_HINT } from "./goalwizard.js";
import { ReleasesFrom, useReleasesFrom } from "./release.js";
import { PartyBands, PriceLine, CanTake, ChecksBlock, OwnParties, TASKMASTER, IDEATION_STAYS, partyWords, pitchParty, usePartyPrice, useOwnParties } from "./party.js";

export const PRIORITIES = [["high", "High"], ["normal", "Normal"], ["low", "Low"]];

export function GoalDialog({ slug = "", then = "", preset = "" }) {
  return slug ? html`<${GoalEdit} slug=${slug} then=${then} />` : html`<${GoalWizard} then=${then} preset=${preset} />`;
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
  const [partyId, setPartyId] = useState("");                // a saved party of the person's picked here, until a seat changes
  const [owns, loadOwns] = useOwnParties(changing);
  const seat = (set) => (v) => { set(v); setPartyId(""); };
  const pickOwn = (p) => { setLeader(p.leader || TASKMASTER); setTeam([...p.team]); setEvery([...p.every]); setPartyId(p.id); };
  const price = usePartyPrice(changing, leader, team, every, g?.craft || "");          // asked when the party is picked (Change the party)
  const shown = (mapData.value?.goals || []).find((x) => x.slug === slug);            // the Map's party: what it offers and takes releases from (spec 68 §7.6)
  const rf = useReleasesFrom({ self: slug, saved: shown?.releases_from || [], leads: shown?.leader?.slug === "release-manager", offers: (shown?.types || []).some((t) => t.id === "release") });
  const moved = leader !== was.leader || JSON.stringify(team) !== JSON.stringify(was.team) || JSON.stringify(every) !== JSON.stringify(was.every);
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const args = { slug, about: about.trim(), priority };
    if (title.trim() && title.trim() !== g?.title) args.title = title.trim();     // a name typed is the person's
    if (moved || partyId) Object.assign(args, { leader, team, every: every.filter((id) => team.includes(id)), ...(partyId ? { party: partyId } : {}) });   // the party, when changed
    const from = rf.value();
    if (from) args.releases_from = from;
    const got = await act("ideas.goal_save", args);
    setSaving(false);
    if (!got?.slug) return;
    for (const note of got.notes || []) toast(note);
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };
  return html`<${Modal} title="Edit the party" onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save party</button>`}>
    <form id="goal-form" class="shell-form" onSubmit=${save}>
      <label class="shell-field"><span class="ok-font-label">Name</span>
        <input class="ork-field" value=${title} aria-label="Name" placeholder="The Taskmaster wrote it; correct it here" maxlength="120" onInput=${(e) => setTitle(e.target.value)} /></label>
      <label class="shell-field"><span class="ok-font-label">What it is for</span>
        <input class="ork-field" autofocus value=${about} aria-label="What it is for" placeholder="One line: what this party is for" onInput=${(e) => setAbout(e.target.value)} /></label>
      ${g && html`<div class="shell-field" role="group" aria-label="The party"><span class="ok-font-label">The party</span>
        <p class="ok-tone-muted shell-party-line">${partyWords(leader, team)}</p>
        ${changing ? html`<${OwnParties} parties=${owns} onPick=${pickOwn} reload=${loadOwns} picked=${partyId} />
          <${PartyBands} craft=${g.craft} leader=${leader} setLeader=${seat(setLeader)} team=${team} setTeam=${seat(setTeam)} />
          <${PriceLine} price=${price} />
          <${CanTake} price=${price} />
          <${ChecksBlock} team=${team} every=${every} setEvery=${seat(setEvery)} price=${price} />`
          : pitchParty(leader) ? html`<p class="ok-tone-muted">${IDEATION_STAYS}</p>`
          : html`<button type="button" class="ork-btn" onClick=${() => setChanging(true)}>Change the party</button>`}</div>`}
      <${ReleasesFrom} rf=${rf} />
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span><small class="ok-tone-muted">${FOR_HINT}</small>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say(`${g?.leader?.slug && g.leader.slug !== TASKMASTER ? g.leader.name : "The Taskmaster"} reads the repository and writes the summary.`)}</p>
    </form>
  <//>`;
}
