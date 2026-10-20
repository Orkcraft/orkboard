// New goal on the desktop in three steps, as on the phone (pwa/shell-goal-new.js): 1. its craft — five tiles, the race's head on
// each (decisions §53), and Mixed —; 2. its party in three bands of seats (ideas.roles `seats`, `parties`, realm/library.py): Leads
// (one: the goal's steps run as it, and it accepts the goal; the Taskmaster when none), Builds (three at most), Checks (two at most);
// the craft's party in them at once, a click takes an agent in or out of its band —; 3. what it is for — the description, the
// priority and the checkers' checks (where each applies or on every idea, and what it adds to an idea) —, Save goal. A task goes to
// the one of the party who does its kind of work; a checker's check adds its line to the spec's Done when and its task to the plan
// (realm/idea_checks.py). Above the bands, Your parties (party.js): a tap fills the craft and the seats and keeps the party's id for the save.
import { useState } from "preact/hooks";
import { html } from "../html.js";
import { say, toast } from "../link.js";
import { track } from "../board/store.js";
import { act, roles, showGoal } from "./store.js";
import { Modal, closeDialog, openDialog } from "./modals.js";
import { Head, CRAFT_WORDS, RACE_WORDS } from "../orkui.js";
import { PRIORITIES } from "./goaldialog.js";
import { CRAFTS, TASKMASTER, PartyBands, ChecksBlock, PriceLine, OwnParties, agentOf, partyWords, usePartyPrice, useOwnParties } from "./party.js";

const MIXED = "mixed";

export function GoalWizard({ then = "" }) {
  const partyOf = (c) => roles.value?.parties?.[c] || { lead: TASKMASTER, build: [], check: [] };
  const [step, setStep] = useState(1);
  const [craft, setCraft] = useState("");
  const [leader, setLeader] = useState(TASKMASTER);
  const [team, setTeam] = useState([]);                  // the builders and checkers
  const [every, setEvery] = useState([]);
  const [about, setAbout] = useState("");
  const [priority, setPriority] = useState("normal");
  const [saving, setSaving] = useState(false);
  const [party, setParty] = useState("");                // the id of the person's own party the seats were filled from; a seat changed drops it
  const [mine, reload] = useOwnParties(step >= 2);
  const seats = (set) => (v) => { setParty(""); set(v); };

  const takeParty = (p) => {                             // Your parties: its craft, its seats and its id
    setCraft(p.craft);
    setLeader(p.leader || TASKMASTER);
    setTeam([...p.team]);
    setEvery([...p.every]);
    setParty(p.id);
  };
  const pick = (c) => {
    if (c !== craft) {
      setParty("");
      const p = partyOf(c);
      setCraft(c);
      setLeader(p.lead || TASKMASTER);
      setTeam([...p.build, ...p.check]);
    }
    setStep(2);
  };
  const craftOf = () => {
    if (craft !== MIXED) return craft;
    const crafts = [leader, ...team].filter((id) => id !== TASKMASTER).map((id) => agentOf(id)?.craft).filter(Boolean);
    return crafts.sort((a, b) => crafts.filter((x) => x === b).length - crafts.filter((x) => x === a).length)[0] || "engineering";
  };
  const price = usePartyPrice(step >= 2, leader, team, every, step >= 2 ? craftOf() : "");   // what an idea costs with this party and its hints (spec 43 C, E)
  const save = async (e) => {
    e?.preventDefault();
    if (!about.trim() || saving) return;
    setSaving(true);
    const got = await act("ideas.goal_save", { about: about.trim(), craft: craftOf(), leader, team, every: every.filter((id) => team.includes(id)), priority, ...(party ? { party } : {}) });
    setSaving(false);
    if (!got?.slug) return;
    (got.notes || []).forEach((n) => toast(n));          // an agent of the party's the project has already: kept as it is
    closeDialog();
    track.value = got.slug;
    if (then === "idea") openDialog("idea", { goal: got.slug });
    else showGoal(got.slug);
  };

  const steps = html`<ol class="shell-steps" aria-label=${`Step ${step} of 3`}>${["Craft", "Team", "What for"].map((w, i) => html`<li key=${w}
    class=${i + 1 === step ? "is-on" : i + 1 < step ? "is-done" : ""}>${w}</li>`)}</ol>`;
  let body, foot;
  if (step === 1) {
    body = html`<p class="ok-tone-muted">What kind of goal is it? Its craft picks the party it starts with.</p>
      <div class="shell-craft-tiles">${CRAFTS.map(([c, race, line]) => html`<button type="button" key=${c} class="shell-craft-tile" data-craft=${c}
          aria-pressed=${String(c === craft)} onClick=${() => pick(c)}><${Head} race=${race} /><b>${CRAFT_WORDS[c]}</b>
          <small class="ok-tone-muted">${RACE_WORDS[race]} · ${line}</small></button>`)}
        <button type="button" class="shell-craft-tile mixed" data-craft=${MIXED} aria-pressed=${String(craft === MIXED)} onClick=${() => pick(MIXED)}>
          <span class="shell-craft-heads">${CRAFTS.map(([c, race]) => html`<${Head} key=${c} race=${race} small=${true} />`)}</span><b>Mixed</b>
          <small class="ok-tone-muted">A party of any crafts: the Taskmaster leads, you pick the rest</small></button></div>`;
    foot = html`<button type="button" class="ork-btn" onClick=${closeDialog}>Cancel</button>`;
  } else if (step === 2) {
    body = html`<p class="ok-tone-muted">The goal's party: its leader plans and accepts, its builders work, its checkers check. A task goes to the one who does its kind of work; Grunt fills in.</p>
      <${OwnParties} parties=${mine} picked=${party} onPick=${takeParty} reload=${reload} />
      <${PartyBands} craft=${craft} leader=${leader} setLeader=${seats(setLeader)} team=${team} setTeam=${seats(setTeam)} />
      <${PriceLine} price=${price} />`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(1)}>Back</button>
      <button type="button" class="ork-btn primary" onClick=${() => setStep(3)}>Next</button>`;
  } else {
    const lead = agentOf(leader);
    body = html`<form id="goal-form" class="shell-form" onSubmit=${save}>
      <p class="ok-tone-muted shell-party-line">${craft === MIXED ? `Mixed, mostly ${CRAFT_WORDS[craftOf()]}` : CRAFT_WORDS[craft]} · ${partyWords(leader, team)}</p>
      <label class="shell-field"><span class="ok-font-label">Description</span>
        <textarea class="ork-field" rows="5" autofocus value=${about} aria-label="Description" placeholder="A few lines: what you want to reach, and why"
          onInput=${(e) => setAbout(e.target.value)}></textarea></label>
      <div class="shell-field" role="group" aria-label="Priority"><span class="ok-font-label">Priority</span>
        <div class="shell-seg">${PRIORITIES.map(([id, name]) => html`<label key=${id} class=${`shell-seg__one${priority === id ? " is-on" : ""}`}>
          <input type="radio" name="priority" class="gui-onb__hide" checked=${priority === id} onChange=${() => setPriority(id)} />${name}</label>`)}</div></div>
      <p class="ok-font-status ok-tone-muted">${say(`${lead?.name || "The Taskmaster"} reads the repository and writes the title, the summary, the metrics and the links.`)}</p>
      <${ChecksBlock} team=${team} every=${every} setEvery=${seats(setEvery)} price=${price} />
    </form>`;
    foot = html`<button type="button" class="ork-btn" onClick=${() => setStep(2)}>Back</button>
      <button type="submit" form="goal-form" class="ork-btn primary" disabled=${!about.trim() || saving}>Save goal</button>`;
  }
  return html`<${Modal} title="New goal" onClose=${closeDialog} wide=${true} foot=${foot}>${steps}${body}<//>`;
}
