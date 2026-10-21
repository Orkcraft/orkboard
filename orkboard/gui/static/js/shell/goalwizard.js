// New party (docs/specs/50-parties-and-goals.md §3.7), one screen: its name, *What it is for* (one line), the party — *one of yours, or from the library*: the
// leader, builders and checkers in three bands of seats (ideas.roles `seats`, `parties`, realm/library.py), a click takes an agent in or out of its band,
// with what the party costs a goal (spec 43 §3) —, the checks on every goal and its priority (*goes first when the window is short*). No metrics, no deadline,
// no links: a party has no end. It sends `ideas.goal_save` with `title`, `about`, `team`, `every`, `leader`, `party` (a party of the person's that was picked) and
// `priority`. A task goes to the one of the party who does its kind of work; a checker's check adds its line to a goal's Done when and its task to the plan
// (realm/idea_checks.py). The code's goal is a party.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { track } from "../board/store.js";
import { act, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { Head, CRAFT_WORDS } from "../orkui.js";
import { PRIORITIES } from "./goaldialog.js";
import { CRAFTS, TASKMASTER, PartyBands, PriceLine, ChecksBlock, OwnParties, agentOf, partyWords, usePartyPrice, useOwnParties } from "./party.js";

export const FOR_HINT = "goes first when the window is short";

export function GoalWizard({ then = "" }) {
  const library = (c) => roles.value?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
  const start = library("engineering");
  const [title, setTitle] = useState("");
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [craft, setCraft] = useState("engineering");     // the library's party the seats started from: its agents are listed first in each band
  const [leader, setLeader] = useState(start.lead || TASKMASTER);
  const [team, setTeam] = useState([...(start.build || []), ...(start.check || [])]);
  const [every, setEvery] = useState([]);
  const [saving, setSaving] = useState(false);
  const [partyId, setPartyId] = useState("");              // the saved party of the person's whose seats these are, until a seat changes
  const [owns, loadOwns] = useOwnParties(true);
  const seat = (set) => (v) => { set(v); setPartyId(""); };      // a seat changed afterwards: the party is then the person's own picking
  const pickOwn = (p) => {
    if (p.craft) setCraft(p.craft);
    setLeader(p.leader || TASKMASTER);
    setTeam([...p.team]);
    setEvery([...p.every]);
    setPartyId(p.id);
  };
  const fromLibrary = (c) => { const p = library(c); setCraft(c); setPartyId(""); setLeader(p.lead || TASKMASTER); setTeam([...(p.build || []), ...(p.check || [])]); setEvery([]); };
  const price = usePartyPrice(true, leader, team, every, craft);
  const ready = (title.trim() || about.trim()) && !saving;
  const save = async (e) => {
    e?.preventDefault();
    if (!ready) return;
    setSaving(true);
    const got = await act("ideas.goal_save", { ...(title.trim() ? { title: title.trim() } : {}), about: about.trim(), leader, team, every: every.filter((id) => team.includes(id)), priority,
      ...(partyId ? { party: partyId } : {}) });
    setSaving(false);
    if (!got?.slug) return;
    for (const note of got.notes || []) toast(note);       // an agent of the project's own that the party carries stays as it was
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };
  return html`<${Modal} title="New party" onClose=${closeDialog} wide=${true}
    foot=${html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!ready}>Save party</button>`}>
    <form id="goal-form" class="shell-form" onSubmit=${save}>
      <label class="shell-field"><span class="ok-font-label">Name</span>
        <input class="ork-field" autofocus value=${title} aria-label="Name" placeholder="Its name, in a few words" maxlength="120" onInput=${(e) => setTitle(e.target.value)} /></label>
      <label class="shell-field"><span class="ok-font-label">What it is for</span>
        <input class="ork-field" value=${about} aria-label="What it is for" placeholder="One line: what this party is for" onInput=${(e) => setAbout(e.target.value)} /></label>
      <div class="shell-field" role="group" aria-label="The party"><span class="ok-font-label">The party</span>
        <p class="ok-tone-muted">One of yours, or from the library: its leader plans, its builders work, its checkers check. A task goes to the one who does its kind of work; Grunt fills in.</p>
        <div class="shell-craft-tiles" role="group" aria-label="From the library">${CRAFTS.map(([c, race, line]) => html`<button type="button" key=${c} class="shell-craft-tile" data-craft=${c}
          aria-pressed=${String(c === craft && !partyId)} title=${line} onClick=${() => fromLibrary(c)}><${Head} race=${race} small=${true} /><b>${CRAFT_WORDS[c]}</b></button>`)}</div>
        <${OwnParties} parties=${owns} onPick=${pickOwn} reload=${loadOwns} picked=${partyId} />
        <${PartyBands} craft=${craft} leader=${leader} setLeader=${seat(setLeader)} team=${team} setTeam=${seat(setTeam)} />
        <${PriceLine} price=${price} />
        <p class="ok-tone-muted shell-party-line">${partyWords(leader, team)}</p></div>
      <${ChecksBlock} team=${team} every=${every} setEvery=${seat(setEvery)} price=${price} />
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span><small class="ok-tone-muted">${FOR_HINT}</small>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say(`${agentOf(leader)?.name || "The Taskmaster"} reads the repository and writes the summary.`)}</p>
    </form>
  <//>`;
}
